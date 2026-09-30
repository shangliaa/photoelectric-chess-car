# motor.py — 四路智能电机驱动模块通信
# 驱动板：AT8236×4 + MCU 协处理器，UART2 通信，内置 PID 与编码器读取
# 通道映射：M1=左前, M2=左后, M3=右前, M4=右后
# 用法：
#   dm = DualMotor()
#   dm.configure()        # 上电配置电机参数（只需执行一次，驱动板断电保存）
#   dm.set_speeds(50, 50) # 左右侧速度 -100~100，同侧前后轮同速

from machine import UART, Pin
import time
import config


class MotorDriver:
    """四路智能电机驱动板 UART 通信封装。"""

    def __init__(self):
        self._uart = UART(2, baudrate=config.MOTOR_UART_BAUDRATE,
                          tx=Pin(config.PIN_UART2_TX), rx=Pin(config.PIN_UART2_RX))
        self._rx_buf = ''
        # 编码器总脉冲缓存（M1=左前, M2=左后, M3=右前, M4=右后）
        self.enc = [0, 0, 0, 0]

    def _send(self, text):
        self._uart.write(text + '\n')

    def _read_line(self, timeout_ms=100):
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            if self._uart.any():
                data = self._uart.read().decode('utf-8', errors='ignore')
                self._rx_buf += data
                if '\n' in self._rx_buf:
                    line, self._rx_buf = self._rx_buf.split('\n', 1)
                    return line.strip()
            time.sleep_ms(2)
        return None

    def configure(self):
        """上电配置电机参数（驱动板断电保存，只需执行一次）。"""
        cmds = [
            f'$mtype:{config.MOTOR_TYPE}#',
            f'$mphase:{config.MOTOR_GEAR_RATIO}#',
            f'$mline:{config.MOTOR_PHASE_LINES}#',
            f'$wdiameter:{config.MOTOR_WHEEL_DIAMETER}#',
            f'$deadzone:{config.MOTOR_DEADZONE}#',
            '$upload:1,0,0#',  # 启用编码器总脉冲连续上报
        ]
        for cmd in cmds:
            self._send(cmd)
            time.sleep_ms(120)  # 配置指令间隔需 ≥100ms
        print('电机驱动参数已配置，编码器上报已开启')

    def set_speeds(self, m1, m2, m3, m4):
        """设置 4 个电机速度（-1000~1000）。"""
        self._send(f'$spd:{m1},{m2},{m3},{m4}#')

    def set_pwm(self, m1, m2, m3, m4):
        """直接设置 PWM（-3600~3600），无 PID。"""
        self._send(f'$pwm:{m1},{m2},{m3},{m4}#')

    def poll_encoders(self):
        """非阻塞解析 UART 缓冲区中的编码器数据，更新 enc 缓存。"""
        while self._uart.any():
            data = self._uart.read().decode('utf-8', errors='ignore')
            self._rx_buf += data
            while '\n' in self._rx_buf:
                line, self._rx_buf = self._rx_buf.split('\n', 1)
                line = line.strip()
                if line.startswith('$MAll:'):
                    payload = line[5:].rstrip('#')
                    try:
                        vals = [int(x) for x in payload.split(',')]
                        if len(vals) == 4:
                            self.enc = vals
                    except (ValueError, IndexError):
                        pass
        return self.enc

    def stop(self):
        self.set_speeds(0, 0, 0, 0)


class DualMotor:
    """四驱封装，对外接口 set_speeds(left_pct, right_pct)。
    同侧前后轮接收相同速度指令；编码器取左前(M1)、右前(M3)。"""

    def __init__(self):
        self.driver = MotorDriver()
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
        """周期调用：解析编码器上报数据（驱动板内置 PID，无需软件调速）。"""
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


# ---- 单元测试：串口发送速度指令，观察电机转动 ----
if __name__ == '__main__':
    dm = DualMotor()
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
