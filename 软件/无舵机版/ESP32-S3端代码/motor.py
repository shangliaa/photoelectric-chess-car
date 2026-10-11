# motor.py — 四路智能电机驱动模块通信（I2C 版）
# 驱动板：AT8236×4 + MCU 协处理器，I2C 地址 0x26，内置 PID 与编码器读取
# 通道映射：M1=左前, M2=左后, M3=右前, M4=右后
#
# 寄存器协议（官方 IIC通信协议.xlsx，端序与官方 ESP32 C 例程逐字节一致）：
#   0x01 电机类型(u8)   0x02 死区(u16 大端)  0x03 磁环线数(u16 大端)
#   0x04 减速比(u16 大端)  0x05 轮径(float 小端)
#   0x06 速度控制(4×int16 大端, -1000~1000)   0x07 PWM 控制(4×int16 大端, -3600~3600)
#   0x20/0x21 = M1 编码器总脉冲 高16位/低16位（各 u16 大端，拼成有符号 32 位）
#   0x22/0x23 = M2    0x24/0x25 = M3    0x26/0x27 = M4
#
# 用法：
#   dm = DualMotor(i2c)
#   dm.configure()        # 上电配置电机参数（只需执行一次，驱动板断电保存）
#   dm.set_speeds(50, 50) # 左右侧速度 -100~100，同侧前后轮同速

import struct
import time
from machine import I2C
import config

# 寄存器地址
REG_MOTOR_TYPE = 0x01
REG_DEADZONE = 0x02
REG_PULSE_LINES = 0x03
REG_GEAR_RATIO = 0x04
REG_WHEEL_DIA = 0x05
REG_SPEED = 0x06
REG_PWM = 0x07
REG_ENC_TOTAL_HIGH = (0x20, 0x22, 0x24, 0x26)  # M1~M4 总脉冲高16位寄存器
REG_ENC_TOTAL_LOW = (0x21, 0x23, 0x25, 0x27)  # M1~M4 总脉冲低16位寄存器


class MotorDriver:
    """四路智能电机驱动板 I2C 通信封装。"""

    def __init__(self, i2c: I2C, addr=config.MOTOR_I2C_ADDR):
        self._i2c = i2c
        self._addr = addr
        # 编码器总脉冲缓存（M1=左前, M2=左后, M3=右前, M4=右后）
        self.enc = [0, 0, 0, 0]

    # ---------- 底层读写 ----------
    def _write_reg(self, reg, data):
        self._i2c.writeto_mem(self._addr, reg, bytes(data))

    def _read_reg(self, reg, n):
        return self._i2c.readfrom_mem(self._addr, reg, n)

    # ---------- 配置 ----------
    def configure(self):
        """上电写入电机参数（驱动板断电保存，重复写入无害）。"""
        self._write_reg(REG_MOTOR_TYPE, [config.MOTOR_TYPE])
        time.sleep_ms(10)
        dz = config.MOTOR_DEADZONE & 0xFFFF
        self._write_reg(REG_DEADZONE, [(dz >> 8) & 0xFF, dz & 0xFF])
        time.sleep_ms(10)
        pl = config.MOTOR_PHASE_LINES & 0xFFFF
        self._write_reg(REG_PULSE_LINES, [(pl >> 8) & 0xFF, pl & 0xFF])
        time.sleep_ms(10)
        gr = config.MOTOR_GEAR_RATIO & 0xFFFF
        self._write_reg(REG_GEAR_RATIO, [(gr >> 8) & 0xFF, gr & 0xFF])
        time.sleep_ms(10)
        self._write_reg(REG_WHEEL_DIA, list(struct.pack('<f', config.MOTOR_WHEEL_DIAMETER)))
        time.sleep_ms(10)
        print('电机驱动参数已写入(I2C)')

    # ---------- 控制 ----------
    def set_speeds(self, m1, m2, m3, m4):
        """设置 4 个电机速度（-1000~1000，驱动板内置 PID）。"""
        self._write_reg(REG_SPEED, list(struct.pack('>hhhh', int(m1), int(m2), int(m3), int(m4))))

    def set_pwm(self, m1, m2, m3, m4):
        """直接设置 PWM（-3600~3600），无 PID。"""
        self._write_reg(REG_PWM, list(struct.pack('>hhhh', int(m1), int(m2), int(m3), int(m4))))

    def stop(self):
        self.set_speeds(0, 0, 0, 0)

    # ---------- 编码器 ----------
    def _read_total(self, idx):
        """读 32 位编码器总脉冲（有符号）。
        防进位跳变：总脉冲拆高/低两个 16 位寄存器，读取间隙可能进位——
        先读高、再读低、复读高，若高变化则用新高低重读低位。"""
        high_reg = REG_ENC_TOTAL_HIGH[idx]
        low_reg = REG_ENC_TOTAL_LOW[idx]
        h1 = int.from_bytes(self._read_reg(high_reg, 2), 'big')
        lo = int.from_bytes(self._read_reg(low_reg, 2), 'big')
        h2 = int.from_bytes(self._read_reg(high_reg, 2), 'big')
        if h1 != h2:
            lo = int.from_bytes(self._read_reg(low_reg, 2), 'big')
            h1 = h2
        v = (h1 << 16) | lo
        if v >= 0x80000000:
            v -= 0x100000000
        return v

    def poll_encoders(self):
        """更新编码器总脉冲缓存（只读前轮 M1/M3，motion 航迹推算仅用前轮）。"""
        self.enc[0] = self._read_total(0)  # M1 左前
        self.enc[2] = self._read_total(2)  # M3 右前
        return self.enc


class DualMotor:
    """四驱封装，对外接口 set_speeds(left_pct, right_pct)。
    同侧前后轮接收相同速度指令；编码器取左前(M1)、右前(M3)。"""

    def __init__(self, i2c: I2C):
        self.driver = MotorDriver(i2c)
        # 方向符号：若实测电机转向相反，将对应侧改为 -1
        self._left_sign = 1
        self._right_sign = 1

    def configure(self):
        self.driver.configure()

    def set_speeds(self, left_pct, right_pct):
        """设置左右侧速度占空比 -100~100（负=反转）。"""
        # 百分比 -> 驱动速度(-1000~1000)
        left = int(left_pct / 100.0 * config.MOTOR_SPEED_MAX) * self._left_sign
        right = int(right_pct / 100.0 * config.MOTOR_SPEED_MAX) * self._right_sign
        self.driver.set_speeds(left, left, right, right)

    def stop(self):
        self.driver.stop()

    def update(self):
        """周期调用：轮询编码器（驱动板内置 PID，无需软件调速）。"""
        self.driver.poll_encoders()

    @property
    def enc_l(self):
        """左前编码器总脉冲（M1）。"""
        return _EncoderProxy(self.driver, 0)

    @property
    def enc_r(self):
        """右前编码器总脉冲（M3）。"""
        return _EncoderProxy(self.driver, 2)


class _EncoderProxy:
    """编码器计数代理，使 motion.py 可通过 .count 访问。"""

    def __init__(self, driver, index):
        self._driver = driver
        self._idx = index

    @property
    def count(self):
        return self._driver.enc[self._idx]


# ---- 单元测试：I2C 控速 + 观察编码器脉冲 ----
if __name__ == '__main__':
    from machine import Pin
    i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=config.I2C_FREQ)
    print('I2C 设备:', [hex(a) for a in i2c.scan()])
    dm = DualMotor(i2c)
    print('配置电机参数...')
    dm.configure()
    print('前进 2 秒 (L=50, R=50)')
    dm.set_speeds(50, 50)
    time.sleep(2)
    dm.update()
    print(f'编码器 L={dm.enc_l.count} R={dm.enc_r.count}')
    print('差速转向 2 秒')
    dm.set_speeds(-30, 30)
    time.sleep(2)
    dm.stop()
    dm.update()
    print(f'编码器 L={dm.enc_l.count} R={dm.enc_r.count}')
