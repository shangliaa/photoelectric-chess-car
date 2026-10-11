# tinyf.py — TinyF 激光测距模块驱动（UART2）
# 亚博 TinyF（与微雪 TOF MINIF 同款）：115200 8N1，ASCII 帧主动输出，约 30Hz
# 帧格式："距离, 状态\n"（帧头空格0x20，距离为mm十进制ASCII，分隔", "，状态0=有效）
# 模块引脚：1=VDD 5V, 2=RX, 3=TX, 4=GND（5/6 脚悬空）
# 安装位置：车头中央，检测前方障碍物（挡板/对方车辆）

import time
from machine import UART, Pin
import config


class TinyF:
    """TinyF 激光测距（单模块，车头中央）。"""

    def __init__(self, uart_id=2):
        self._uart = UART(uart_id, baudrate=config.TINYF_BAUDRATE,
                          tx=Pin(config.PIN_TINYF_TX), rx=Pin(config.PIN_TINYF_RX))
        self._buf = ''
        self._dist = -1        # 最新有效距离（mm）
        self._last_ms = 0      # 最新有效帧时间戳

    def _parse(self, line):
        """解析一行 ASCII 帧，如 ' 327, 0'。"""
        line = line.strip()
        if not line:
            return
        try:
            parts = line.split(',')
            dist = int(parts[0].strip())
            status = int(parts[1].strip()) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            return
        if status != 0:
            return  # 状态非 0：本次测量无效
        if dist < 0 or dist > config.TINYF_MAX_RANGE_MM:
            return  # 超出量程
        self._dist = dist
        self._last_ms = time.ticks_ms()

    def poll(self):
        """非阻塞解析串口缓冲区，多帧只留最新。返回缓存的最新距离（无则 -1）。"""
        if self._uart.any():
            data = self._uart.read()
            if data:
                self._buf += data.decode('ascii', errors='ignore')
                while '\n' in self._buf:
                    line, self._buf = self._buf.split('\n', 1)
                    self._parse(line)
        return self._dist

    def read_range(self):
        """返回最新有效距离（mm）；无有效数据或数据过期返回 -1。
        -1 在避障逻辑中视为「无障碍」，不会误停。"""
        self.poll()
        if self._dist < 0:
            return -1
        if time.ticks_diff(time.ticks_ms(), self._last_ms) > config.TINYF_TIMEOUT_MS:
            return -1
        return self._dist


# ---- 单元测试：串口打印前方距离，用手遮挡测试 ----
if __name__ == '__main__':
    tf = TinyF()
    print('TinyF 测距测试（遮挡观察数值变化）：')
    while True:
        d = tf.read_range()
        print(f'dist={d}mm')
        time.sleep_ms(200)
