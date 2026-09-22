# config.py — K230 视觉端配置
# 颜色阈值使用 LAB 色彩空间 (L, A, B)，格式 (Lmin, Lmax, Amin, Amax, Bmin, Bmax)
# ⚠️ 阈值需在赛场光线下现场校准！下方仅为初始参考值

# 图像分辨率
IMG_WIDTH = 640
IMG_HEIGHT = 480
IMG_CENTER_X = IMG_WIDTH // 2

# 己方棋子颜色（默认红方，若为黑方将 MY_COLOR 改为 'black'）
MY_COLOR = 'red'

# LAB 阈值
# 红色棋子（红漆棋子）—— 需按现场调整
RED_THRESHOLD = (0, 80, 20, 127, 10, 127)
# 黑色棋子（深色棋子）—— 需按现场调整
BLACK_THRESHOLD = (0, 60, -30, 30, -30, 30)

# 球门区域颜色阈值 —— 赛场球门区颜色未知，必须现场校准
# 示例：若球门区为蓝色，可参考 (43, 99, -43, -4, -56, -7)
GOAL_THRESHOLD = (43, 99, -43, -4, -56, -7)

# 色块过滤参数
BLOB_AREA_MIN = 500        # 最小面积（像素），过滤噪声
BLOB_AREA_MAX = 50000      # 最大面积
BLOB_MARGIN = 20           # 距图像边缘的安全边距

# 视觉伺服参数
SERVO_DEADZONE_PX = 40     # 棋子居中死区（像素），小于此值不转向
SERVO_TURN_KP = 0.15       # 像素偏差 -> 转向角度系数
MOVE_STEP_MM = 40          # 每次前进步进距离（mm）
MOVE_SPEED = 50            # 前进速度占空比
TURN_SPEED = 40            # 转向速度占空比
GOAL_OVERLAP_RATIO = 0.5   # 棋子与球门重叠比例阈值，超过判定进球

# 串口
UART_BAUDRATE = 115200
