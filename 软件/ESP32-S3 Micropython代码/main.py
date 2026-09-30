# main.py — ESP32-S3 运动控制主程序
# 上电初始化 -> IMU 校准 -> 主循环：串口指令解析 + 运动执行 + 状态回传

import time
from machine import I2C, Pin
import config
from motion import MotionController
from uart_protocol import Protocol

print('ESP32-S3 运动控制启动...')

# I2C 总线（MPU6050 + 2x VL53L0X）
i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=config.I2C_FREQ)
print('I2C 设备:', [hex(a) for a in i2c.scan()])

# 运动控制器（内含电机、编码器、IMU、测距）
motion = MotionController(i2c)
# 配置四路智能电机驱动板参数（上电执行一次，驱动板断电保存）
motion.motors.configure()
# 通信协议（云台由 K230 直接控制）
proto = Protocol(motion)

print('初始化完成，等待 K230 指令...')
proto.send('READY')

# 心跳计时
last_hb = time.ticks_ms()
HB_INTERVAL = 1000  # 1s 心跳

while True:
    # 1. 处理串口指令
    proto.poll()
    # 2. 运动更新（PID + 航迹推算 + 避障）
    motion.update()
    # 3. 周期心跳：回传位姿
    now = time.ticks_ms()
    if time.ticks_diff(now, last_hb) >= HB_INTERVAL:
        last_hb = now
        proto.send_pose()
    # 小延时，避免 CPU 满载
    time.sleep_ms(5)
