# config.py — ESP32-S3 全局配置（引脚、物理参数、运动参数）
# 所有可调参数集中在此，接线改动只需修改本文件
# 底盘：四驱轮式小车（4× TT 编码器电机，四路智能电机驱动模块）
# 电机驱动：四路智能驱动板（AT8236×4 + MCU 协处理器），I2C 通信（地址 0x26），内置 PID + 编码器
# 姿态：亚博 9 轴无气压计高精度 IMU（YB-MRA02），I2C 通信（地址 0x23），板载姿态融合
# 测距：TinyF 激光测距模块 ×1（车头中央），UART 通信，ASCII 帧主动输出

# ===================== I2C 总线 =====================
# 9 轴 IMU (0x23) + 四路电机驱动板 (0x26) 共挂一条总线
# 注意：IMU 协议要求时钟 100kHz，请勿提高 I2C_FREQ
PIN_I2C_SCL = 10
PIN_I2C_SDA = 11
I2C_FREQ = 100000

# ===================== 9 轴 IMU（YB-MRA02）=====================
IMU_I2C_ADDR = 0x23
IMU_EULER_ROLL_REG = 0x26      # 欧拉角寄存器（float，小端，弧度）
IMU_EULER_PITCH_REG = 0x2A
IMU_EULER_YAW_REG = 0x2E
IMU_ALGO_REG = 0x61            # 算法类型寄存器：9 = 九轴算法
IMU_YAW_SIGN = 1.0             # 航向符号系数：若右转时航向减小，改为 -1.0

# ===================== 四路电机驱动板（I2C）=====================
# 通道映射：M1=左前, M2=左后, M3=右前, M4=右后
MOTOR_I2C_ADDR = 0x26
# 驱动板电机参数（上电配置一次，驱动板断电保存）
MOTOR_TYPE = 3           # 3: TT电机(带编码器)
MOTOR_GEAR_RATIO = 45    # 减速比（13线金属单轴TT电机 1:45）
MOTOR_PHASE_LINES = 13   # 磁环线数
MOTOR_WHEEL_DIAMETER = 65  # 轮子直径(mm)
MOTOR_DEADZONE = 1250    # PWM 死区
# 速度指令范围：-1000~1000（驱动板内部 PID）
MOTOR_SPEED_MAX = 1000

# ===================== TinyF 激光测距（UART2）=====================
# TinyF 引脚：1=VDD 5V, 2=RX, 3=TX, 4=GND（5/6 脚悬空）
# 串口 115200 8N1，ASCII 帧 "距离, 状态\n"（距离单位 mm，状态 0=有效），约 30Hz 主动输出
PIN_TINYF_TX = 17         # ESP32 TX -> TinyF RX（引脚2）
PIN_TINYF_RX = 18         # ESP32 RX <- TinyF TX（引脚3）
TINYF_BAUDRATE = 115200
TINYF_TIMEOUT_MS = 100    # 超过此时间无新帧视为数据无效（30Hz 帧间隔约 33ms）
TINYF_MAX_RANGE_MM = 4000  # 量程上限（超出视为无效）

# ===================== 与 K230 通信的串口（UART1）=====================
PIN_UART_TX = 12         # ESP32 TX -> K230 RX
PIN_UART_RX = 13         # ESP32 RX <- K230 TX
UART_BAUDRATE = 115200

# ===================== 扩展预留口 =====================
# 原 VL53L0X XSHUT 引脚已释放，可作扩展使用：
#   GPIO21、GPIO38 —— 空闲（预留：扩展传感器/备用 IO）
# 云台舵机由 K230 直接 PWM 控制（GPIO42/43），不占用 ESP32 引脚

# ===================== 物理参数 =====================
# 四驱轮式小车（65mm 橡胶轮胎，底盘宽 148mm）
WHEEL_DIAMETER_MM = 65.0       # 车轮直径（mm），TT 底盘标配 65mm 橡胶轮
WHEEL_BASE_MM = 148.0          # 左右轮距（mm），按底盘实际宽度修改
# TT 编码器电机（13线金属单轴）：磁环 13 线 × 减速比 45 = 每圈 585 脉冲（AB相4倍频后 2340）
ENCODER_PPR = 13 * 45          # 每圈脉冲数（未4倍频）
PULSES_PER_REV = ENCODER_PPR * 4   # AB相4倍频后每圈脉冲数

# ===================== 运动参数 =====================
MOVE_SPEED_PCT = 50            # 默认前进速度占空比 (%)
TURN_SPEED_PCT = 40            # 默认转向速度占空比 (%)
MOVE_STEP_MM = 50              # 每次前进步进距离（mm），视觉伺服用
TURN_DEADZONE_DEG = 3.0        # 转向死区（度），小于此值不转
OBSTACLE_THRESHOLD_MM = 150    # 避障距离阈值（mm）
