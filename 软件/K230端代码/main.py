# main.py — K230 视觉决策主程序
# 采图 -> 球门/棋子识别 -> 视觉伺服决策 -> 串口下发运动指令

import time
from media.display import *
import config
from vision import Vision
from uart_comm import UartComm
from strategy import Strategy

print('K230 视觉决策启动...')

vision = Vision()
comm = UartComm()
strategy = Strategy(vision, comm)

# 等待 ESP32 就绪
for _ in range(20):
    line = comm.read_line(timeout_ms=100)
    if line and 'READY' in line:
        print('ESP32 已就绪')
        break
else:
    print('未收到 ESP32 READY，继续运行...')

clock = time.clock()

try:
    while True:
        clock.tick()
        img = vision.snapshot()

        # 单步决策
        state_info = strategy.run_once(img)

        # 调试显示
        if strategy.goal:
            vision.draw_blobs(img, [strategy.goal], color=(255, 255, 0))
        pieces = vision.find_my_pieces(img)
        vision.draw_blobs(img, pieces, color=(0, 255, 0))
        if strategy.target_piece:
            vision.draw_blobs(img, [strategy.target_piece], color=(255, 0, 0))

        fps = clock.fps()
        img.draw_string_advanced(0, 0, 24, f'{state_info} FPS:{fps:.1f}', color=(255, 255, 255))

        try:
            Display.show_image(img)
        except Exception:
            pass

except KeyboardInterrupt:
    print('用户中断')
except Exception as e:
    print(f'运行错误: {e}')
finally:
    comm.cmd_stop()
    vision.deinit()
    print('已停止')
