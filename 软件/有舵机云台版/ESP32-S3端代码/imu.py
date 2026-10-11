# imu.py — 亚博 9 轴无气压计高精度 IMU（YB-MRA02）姿态读取
# I2C 地址 0x23，时钟 100kHz，板载姿态融合直接输出欧拉角（float，小端，弧度）
# 无需软件陀螺积分与开机静止校准，航向漂移远小于 MPU6050 软件积分方案
# 接口与旧 MPU6050 驱动保持兼容：heading 属性 / update_heading() / reset_heading()

import math
import struct
from machine import I2C, Pin
import config


class YbImu:
    """9 轴 IMU 姿态传感器（I2C 0x23）。"""

    def __init__(self, i2c: I2C, addr=config.IMU_I2C_ADDR):
        self._i2c = i2c
        self._addr = addr
        self._offset = 0.0    # reset_heading() 记录的原始航向偏移
        self._last_raw = 0.0  # 最近一次原始航向（度）
        self._heading = 0.0
        self._check_algo()

    # ---------- 内部读取 ----------
    def _read_reg(self, reg, n):
        return self._i2c.readfrom_mem(self._addr, reg, n)

    def _check_algo(self):
        """检查算法类型是否为九轴（9），仅提示不阻断。"""
        try:
            algo = self._read_reg(config.IMU_ALGO_REG, 1)[0]
            if algo != 9:
                print(f'警告: IMU 算法类型为 {algo}（非9轴），建议用上位机切换为 9')
            else:
                print(f'IMU 就绪（9轴算法，地址 {hex(self._addr)}）')
        except Exception as e:
            print(f'IMU 算法类型读取失败（不影响使用）: {e}')

    # ---------- 数据读取 ----------
    def read_euler(self):
        """读取欧拉角，返回 (roll, pitch, yaw)，单位：度。"""
        roll = struct.unpack('<f', self._read_reg(config.IMU_EULER_ROLL_REG, 4))[0]
        pitch = struct.unpack('<f', self._read_reg(config.IMU_EULER_PITCH_REG, 4))[0]
        yaw = struct.unpack('<f', self._read_reg(config.IMU_EULER_YAW_REG, 4))[0]
        return (math.degrees(roll), math.degrees(pitch), math.degrees(yaw))

    def update_heading(self):
        """读取 YAW 并更新航向角（度，归一化到 -180~180）。"""
        roll, pitch, yaw = self.read_euler()
        raw = (yaw * config.IMU_YAW_SIGN + 180.0) % 360.0 - 180.0
        self._last_raw = raw
        self._heading = (raw - self._offset + 180.0) % 360.0 - 180.0
        return self._heading

    @property
    def heading(self):
        return self._heading

    def reset_heading(self):
        """以当前朝向为 0°（消除安装/开机带来的初始角）。"""
        self._offset = self._last_raw
        self._heading = 0.0


# ---- 单元测试：旋转小车，串口观察航向角变化 ----
# 验证方法：小车向右（顺时针）旋转时航向应增大；若减小，把 config.IMU_YAW_SIGN 改为 -1.0
if __name__ == '__main__':
    import time
    i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=config.I2C_FREQ)
    print('I2C 设备:', [hex(a) for a in i2c.scan()])
    imu = YbImu(i2c)
    imu.update_heading()
    imu.reset_heading()
    print('旋转小车观察航向（右转应增大）：')
    while True:
        h = imu.update_heading()
        roll, pitch, yaw = imu.read_euler()
        print(f'heading={h:.1f}  raw_yaw={yaw:.1f}  roll={roll:.1f}  pitch={pitch:.1f}')
        time.sleep_ms(100)
