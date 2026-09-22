# config.py — ESP32-S3 全局配置（引脚、物理参数、PID 参数）
# 所有可调参数集中在此，接线改动只需修改本文件

# ===================== 引脚定义 =====================
# TB6612FNG 电机驱动
PIN_MOTOR_L_PWM = 4      # 左电机 PWM
PIN_MOTOR_L_IN1 = 5      # 左电机方向 1
PIN_MOTOR_L_IN2 = 6      # 左电机方向 2
PIN_MOTOR_R_PWM = 7      # 右电机 PWM
PIN_MOTOR_R_IN1 = 15     # 右电机方向 1
PIN_MOTOR_R_IN2 = 16     # 右电机方向 2
PIN_MOTOR_STBY = 14      # TB6612 待机使能（若直连3.3V可设为 None）

# AB 相光电编码器
PIN_ENCODER_L_A = 1      # 左编码器 A 相
PIN_ENCODER_L_B = 2      # 左编码器 B 相
PIN_ENCODER_R_A = 41     # 右编码器 A 相
PIN_ENCODER_R_B = 42     # 右编码器 B 相

# 二自由度云台舵机（SG90M）
PIN_SERVO_PAN = 8        # 水平舵机
PIN_SERVO_TILT = 9       # 俯仰舵机

# I2C 总线（MPU6050 + 2x VL53L0X）
PIN_I2C_SCL = 10
PIN_I2C_SDA = 11
I2C_FREQ = 400000

# VL53L0X 关机脚（用于重置地址，两个模块默认地址都是 0x29）
PIN_VL53L0X_L_XSHUT = 21
PIN_VL53L0X_R_XSHUT = 38

# 与 K230 通信的串口
PIN_UART_TX = 12         # ESP32 TX -> K230 RX
PIN_UART_RX = 13         # ESP32 RX <- K230 TX
UART_BAUDRATE = 115200

# ===================== 物理参数 =====================
WHEEL_DIAMETER_MM = 65.0       # 车轮直径（mm），按实际测量修改
WHEEL_BASE_MM = 140.0          # 左右轮距（mm），按实际测量修改
# 编码器线数：电机 11 极对 × 减速比 90 = 每圈 990 脉冲（AB相4倍频后 3960）
# 若电机规格不同请修改此值
ENCODER_PPR = 11 * 90          # 每圈脉冲数（未4倍频）
PULSES_PER_REV = ENCODER_PPR * 4   # AB相4倍频后每圈脉冲数

# ===================== 电机 PID 参数 =====================
# 速度环 PID（单位：脉冲/周期 -> 目标 PWM 0-1000）
MOTOR_KP = 1.2
MOTOR_KI = 0.15
MOTOR_KD = 0.02
MOTOR_PID_INTERVAL_MS = 20     # PID 计算周期
MOTOR_PWM_MAX = 1000           # PWM 最大值（duty_u16 范围 0-1023 时可调）
MOTOR_PWM_MIN = 0

# ===================== 运动参数 =====================
MOVE_SPEED_PCT = 50            # 默认前进速度占空比 (%)
TURN_SPEED_PCT = 40            # 默认转向速度占空比 (%)
MOVE_STEP_MM = 50              # 每次前进步进距离（mm），视觉伺服用
TURN_DEADZONE_DEG = 3.0        # 转向死区（度），小于此值不转
OBSTACLE_THRESHOLD_MM = 150    # 避障距离阈值（mm）

# ===================== 舵机参数 =====================
SERVO_PAN_MIN = 0              # 水平舵机最小角度
SERVO_PAN_MAX = 180            # 水平舵机最大角度
SERVO_TILT_MIN = 30            # 俯仰舵机最小角度（避免碰到底盘）
SERVO_TILT_MAX = 150           # 俯仰舵机最大角度
SERVO_PAN_CENTER = 90          # 水平居中
SERVO_TILT_CENTER = 90         # 俯仰居中

# ===================== IMU 参数 =====================
IMU_COMP_FILTER_ALPHA = 0.98   # 互补滤波系数（陀螺仪权重）
IMU_CALIBRATION_SAMPLES = 500  # 开机静止校准采样数
