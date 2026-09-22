# uart_protocol.py — K230 <-> ESP32 串口通信协议
# 文本行协议，'\\n' 结尾
#
# 接收（K230 -> ESP32）:
#   MOVE,<dist_mm>,<speed>     前进指定距离
#   TURN,<angle_deg>,<speed>   原地转向
#   STOP                       立即停止
#   SERVO,<pan>,<tilt>         云台角度
#   POSE                       请求位姿
#   SCAN                       云台扫描
#
# 发送（ESP32 -> K230）:
#   POSE,<x>,<y>,<heading>     位姿回传
#   DONE,<cmd>                 指令完成
#   OBSTACLE,<dist>            障碍物

from machine import UART, Pin
import config


class Protocol:
    def __init__(self, motion, gimbal):
        self._uart = UART(1, baudrate=config.UART_BAUDRATE,
                          tx=Pin(config.PIN_UART_TX), rx=Pin(config.PIN_UART_RX))
        self._motion = motion
        self._gimbal = gimbal
        self._rx_buf = ''

    def send(self, text):
        self._uart.write(text + '\n')

    def send_pose(self):
        x, y, h = self._motion.get_pose()
        self.send(f'POSE,{x:.1f},{y:.1f},{h:.1f}')

    def send_done(self, cmd):
        self.send(f'DONE,{cmd}')

    def send_obstacle(self, dist):
        self.send(f'OBSTACLE,{dist}')

    def poll(self):
        """处理接收缓冲区，返回是否有新指令（供主循环判断）。"""
        if self._uart.any():
            data = self._uart.read().decode('utf-8', errors='ignore')
            self._rx_buf += data
            while '\n' in self._rx_buf:
                line, self._rx_buf = self._rx_buf.split('\n', 1)
                self._handle(line.strip())
        # 回传状态
        if self._motion.obstacle:
            self.send_obstacle(config.OBSTACLE_THRESHOLD_MM)

    def _handle(self, line):
        if not line:
            return
        parts = line.split(',')
        cmd = parts[0].upper()
        try:
            if cmd == 'MOVE' and len(parts) >= 2:
                dist = float(parts[1])
                speed = int(parts[2]) if len(parts) >= 3 else None
                self._motion.move_distance(dist, speed)
                self.send_done('MOVE')
            elif cmd == 'TURN' and len(parts) >= 2:
                angle = float(parts[1])
                speed = int(parts[2]) if len(parts) >= 3 else None
                self._motion.turn_angle(angle, speed)
                self.send_done('TURN')
            elif cmd == 'STOP':
                self._motion.stop()
                self.send_done('STOP')
            elif cmd == 'SERVO' and len(parts) >= 3:
                pan = int(parts[1])
                tilt = int(parts[2])
                self._gimbal.set(pan, tilt)
                self.send_done('SERVO')
            elif cmd == 'POSE':
                self.send_pose()
            elif cmd == 'SCAN':
                self._scan()
            else:
                self.send(f'ERR,unknown:{line}')
        except Exception as e:
            self.send(f'ERR,{e}')

    def _scan(self):
        """云台水平扫描一周后回中。"""
        import time
        for a in range(30, 151, 30):
            self._gimbal.pan.set_angle(a)
            time.sleep_ms(300)
        self._gimbal.center()
        self.send_done('SCAN')
