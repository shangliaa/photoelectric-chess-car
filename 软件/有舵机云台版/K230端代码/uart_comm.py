# uart_comm.py — K230 串口通信封装
# 基于亚博智能 K230 的 ybUtils.YbUart 库
# 发送文本指令，接收 ESP32 回传状态

import time
from ybUtils.YbUart import YbUart
import config


class UartComm:
    def __init__(self):
        self.uart = YbUart(baudrate=config.UART_BAUDRATE)
        self._rx_buf = ''

    def send(self, text):
        """发送一条指令（自动加换行）。"""
        self.uart.send(text + '\n')

    # ---- 指令发送 ----
    def cmd_move(self, dist_mm, speed=None):
        speed = speed if speed is not None else config.MOVE_SPEED
        self.send(f'MOVE,{dist_mm},{speed}')

    def cmd_turn(self, angle_deg, speed=None):
        speed = speed if speed is not None else config.TURN_SPEED
        self.send(f'TURN,{angle_deg},{speed}')

    def cmd_stop(self):
        self.send('STOP')

    def cmd_pose(self):
        self.send('POSE')

    # ---- 状态接收 ----
    def read_line(self, timeout_ms=50):
        """非阻塞读取一行（以 \\n 结尾），无数据返回 None。"""
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            data = self.uart.read()
            if data:
                self._rx_buf += data if isinstance(data, str) else data.decode('utf-8', errors='ignore')
                if '\n' in self._rx_buf:
                    line, self._rx_buf = self._rx_buf.split('\n', 1)
                    return line.strip()
            time.sleep_ms(5)
        return None

    def wait_done(self, cmd, timeout_ms=3000):
        """等待指定指令的 DONE 回传，超时返回 False。"""
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            line = self.read_line(timeout_ms=100)
            if line:
                print('ESP32:', line)
                if line.startswith(f'DONE,{cmd}'):
                    return True
                if line.startswith('OBSTACLE'):
                    return False  # 遇障中止
        return False

    def get_pose(self, timeout_ms=1000):
        """请求并解析位姿 (x, y, heading)。"""
        self.cmd_pose()
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            line = self.read_line(timeout_ms=100)
            if line and line.startswith('POSE,'):
                parts = line.split(',')
                try:
                    return float(parts[1]), float(parts[2]), float(parts[3])
                except (IndexError, ValueError):
                    pass
        return None
