# imu.py — MPU6050 六轴姿态传感器 + 航向角解算
# 用陀螺仪 Z 轴角速度积分得到航向，互补滤波抑制漂移
# I2C 地址默认 0x68（AD0 接 GND）

from machine import I2C, Pin
import time
import math
import config

MPU6050_ADDR = 0x68
# 寄存器
REG_SMPLRT_DIV = 0x19
REG_CONFIG = 0x1A
REG_GYRO_CONFIG = 0x1B
REG_ACCEL_CONFIG = 0x1C
REG_ACCEL_XOUT_H = 0x3B
REG_GYRO_XOUT_H = 0x43
REG_PWR_MGMT_1 = 0x6B
REG_WHO_AM_I = 0x75


class MPU6050:
    def __init__(self, i2c: I2C, addr=MPU6050_ADDR):
        self._i2c = i2c
        self._addr = addr
        self._gyro_z_bias = 0.0
        self._heading = 0.0
        self._last_time = 0
        self._init()

    def _write(self, reg, val):
        self._i2c.writeto_mem(self._addr, reg, bytes([val]))

    def _read(self, reg, n):
        return self._i2c.readfrom_mem(self._addr, reg, n)

    def _init(self):
        # 唤醒
        self._write(REG_PWR_MGMT_1, 0x00)
        time.sleep_ms(100)
        # 采样率分频 0 -> 1kHz
        self._write(REG_SMPLRT_DIV, 0x00)
        # 低通滤波 42Hz
        self._write(REG_CONFIG, 0x03)
        # 陀螺仪量程 ±2000°/s
        self._write(REG_GYRO_CONFIG, 0x18)
        # 加速度量程 ±2g
        self._write(REG_ACCEL_CONFIG, 0x00)
        time.sleep_ms(50)

    def who_am_i(self):
        return self._read(REG_WHO_AM_I, 1)[0]

    def _raw(self, reg):
        data = self._read(reg, 6)
        x = (data[0] << 8) | data[1]
        y = (data[2] << 8) | data[3]
        z = (data[4] << 8) | data[5]
        if x >= 0x8000:
            x -= 0x10000
        if y >= 0x8000:
            y -= 0x10000
        if z >= 0x8000:
            z -= 0x10000
        return x, y, z

    def read_accel(self):
        return self._raw(REG_ACCEL_XOUT_H)

    def read_gyro(self):
        return self._raw(REG_GYRO_XOUT_H)

    def calibrate(self, samples=None):
        """开机静止时校准陀螺仪零偏。"""
        if samples is None:
            samples = config.IMU_CALIBRATION_SAMPLES
        print('IMU 校准中，保持静止...')
        total = 0
        for _ in range(samples):
            gx, gy, gz = self.read_gyro()
            total += gz
            time.sleep_ms(2)
        self._gyro_z_bias = total / samples
        self._heading = 0.0
        self._last_time = time.ticks_ms()
        print(f'校准完成 gyro_z_bias={self._gyro_z_bias:.2f}')

    def update_heading(self):
        """读取陀螺仪并积分更新航向角（度）。"""
        gx, gy, gz = self.read_gyro()
        now = time.ticks_ms()
        dt = time.ticks_diff(now, self._last_time) / 1000.0
        self._last_time = now
        # ±2000°/s 量程，灵敏度 16.4 LSB/(°/s)
        gyro_z_dps = (gz - self._gyro_z_bias) / 16.4
        self._heading += gyro_z_dps * dt
        # 归一化到 -180~180
        self._heading = (self._heading + 180) % 360 - 180
        return self._heading

    @property
    def heading(self):
        return self._heading

    def reset_heading(self):
        self._heading = 0.0


# ---- 单元测试：旋转小车，串口观察航向角变化 ----
if __name__ == '__main__':
    i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=config.I2C_FREQ)
    imu = MPU6050(i2c)
    print('WHO_AM_I:', hex(imu.who_am_i()))
    imu.calibrate()
    print('旋转小车观察航向：')
    while True:
        h = imu.update_heading()
        print(f'heading={h:.1f}')
        time.sleep_ms(100)
