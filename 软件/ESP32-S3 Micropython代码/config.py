# config.py — ESP32-S3 全局配置（引脚、物理参数、运动参数）
# 所有可调参数集中在此，接线改动只需修改本文件
# 底盘：四驱轮式小车（4× TT 编码器电机，四路智能电机驱动模块）
# 电机驱动：四路智能驱动板（AT8236×4 + MCU 协处理器），UART2 通信，内置 PID + 编码器

# ===================== 引脚定义 =====================
# 四路智能电机驱动模块（UART2 通信，驱动内置 PID 与编码器读取）
#   M1=左前, M2=左后, M3=右前, M4=右后
PIN_UART2_TX = 17       # ESP32 TX -> 驱动板 RX
PIN_UART2_RX = 18       # ESP32 RX <- 驱动板 TX
MOTOR_UART_BAUDRATE = 115200

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

# 与 K230 通信的串口（UART1）
PIN_UART_TX = 12         # ESP32 TX -> K230 RX
PIN_UART_RX = 13         # ESP32 RX <- K230 TX
UART_BAUDRATE = 115200

# ===================== 电机驱动配置 =====================
# 驱动板电机参数（上电配置一次，驱动板断电保存）
MOTOR_TYPE = 3           # 3: TT电机(带编码器)
MOTOR_GEAR_RATIO = 48    # 减速比
MOTOR_PHASE_LINES = 13   # 磁环线数
MOTOR_WHEEL_DIAMETER = 65  # 轮子直径(mm)
MOTOR_DEADZONE = 1250    # PWM 死区
# 速度指令范围：-1000~1000（驱动板内部 PID）
MOTOR_SPEED_MAX = 1000

# ===================== 物理参数 =====================
# 四驱轮式小车（65mm 橡胶轮胎，底盘宽 148mm）
WHEEL_DIAMETER_MM = 65.0       # 车轮直径（mm），TT 底盘标配 65mm 橡胶轮
WHEEL_BASE_MM = 148.0          # 左右轮距（mm），按底盘实际宽度修改
# TT 编码器电机：磁环 11 极对 × 减速比 48 = 每圈 528 脉冲（AB相4倍频后 2112）
ENCODER_PPR = 11 * 48          # 每圈脉冲数（未4倍频）
PULSES_PER_REV = ENCODER_PPR * 4   # AB相4倍频后每圈脉冲数

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
