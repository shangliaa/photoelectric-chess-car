# strategy.py — 目标选择 + 视觉伺服闭环
# 状态机：找球门 -> 找己方棋子 -> 对准 -> 推进 -> 进球倒车 -> 循环

import time
import config
from vision import Vision
from uart_comm import UartComm
from servo import Gimbal


class Strategy:
    def __init__(self, vision: Vision, comm: UartComm, gimbal: Gimbal):
        self.vision = vision
        self.comm = comm
        self.gimbal = gimbal
        self.state = 'SEARCH_GOAL'   # SEARCH_GOAL / SEARCH_PIECE / ALIGN / PUSH / SCORE / REVERSE
        self.target_piece = None
        self.goal = None
        self.goal_cx = config.IMG_CENTER_X
        self._search_angle = 0

    def run_once(self, img):
        """单步决策，返回状态字符串（供调试打印）。"""
        # 识别球门
        self.goal = self.vision.find_goal(img)
        if self.goal:
            self.goal_cx = self.goal['cx']

        # 识别己方棋子
        pieces = self.vision.find_my_pieces(img)

        if self.state == 'SEARCH_GOAL':
            return self._do_search_goal(img)
        elif self.state == 'SEARCH_PIECE':
            return self._do_search_piece(img, pieces)
        elif self.state == 'ALIGN':
            return self._do_align(img, pieces)
        elif self.state == 'PUSH':
            return self._do_push(img, pieces)
        elif self.state == 'SCORE':
            return self._do_score()
        return 'IDLE'

    # ---------- 状态：找球门 ----------
    def _do_search_goal(self, img):
        if self.goal:
            # 球门已找到，转向使其居中
            err = self.goal['cx'] - config.IMG_CENTER_X
            if abs(err) < config.SERVO_DEADZONE_PX:
                self.state = 'SEARCH_PIECE'
                return 'GOAL_CENTERED'
            angle = err * config.SERVO_TURN_KP
            self.comm.cmd_turn(angle)
            self.comm.wait_done('TURN', timeout_ms=1500)
            return f'TURN_TO_GOAL err={err:.0f}'
        else:
            # 球门未找到，云台扫描 + 小车小角度旋转
            self._search_angle += 30
            if self._search_angle > 180:
                self._search_angle = -180
            self.gimbal.set(90 + self._search_angle // 2, 90)
            time.sleep_ms(300)
            if self._search_angle % 120 == 0:
                self.comm.cmd_turn(45)
                self.comm.wait_done('TURN', timeout_ms=2000)
            return 'SCANNING_GOAL'

    # ---------- 状态：找棋子 ----------
    def _do_search_piece(self, img, pieces):
        if not pieces:
            # 没找到棋子，小角度转头继续找
            self.comm.cmd_turn(30)
            self.comm.wait_done('TURN', timeout_ms=1500)
            return 'NO_PIECE_TURN'
        # 选最居中的棋子作为目标
        self.target_piece = min(pieces, key=lambda p: abs(p['cx'] - config.IMG_CENTER_X))
        self.state = 'ALIGN'
        return f'FOUND_PIECE cx={self.target_piece["cx"]}'

    # ---------- 状态：对准棋子 ----------
    def _do_align(self, img, pieces):
        # 重新匹配目标（取最接近上次目标中心的棋子）
        if pieces:
            self.target_piece = min(pieces, key=lambda p: abs(p['cx'] - self.target_piece['cx']))
            err = self.target_piece['cx'] - config.IMG_CENTER_X
            if abs(err) < config.SERVO_DEADZONE_PX:
                self.state = 'PUSH'
                return 'PIECE_ALIGNED'
            angle = err * config.SERVO_TURN_KP
            self.comm.cmd_turn(angle)
            self.comm.wait_done('TURN', timeout_ms=1000)
            return f'ALIGN err={err:.0f}'
        else:
            self.state = 'SEARCH_PIECE'
            return 'LOST_PIECE'

    # ---------- 状态：推进 ----------
    def _do_push(self, img, pieces):
        # 检查是否进球：棋子与球门重叠
        if self.goal and pieces:
            piece = min(pieces, key=lambda p: abs(p['cx'] - self.target_piece['cx']))
            self.target_piece = piece
            if self._is_goal_overlap(piece, self.goal):
                self.state = 'SCORE'
                return 'GOAL_OVERLAP'
            # 棋子变大说明接近，可加大检测
            if piece['area'] > 30000:
                self.state = 'SCORE'
                return 'PIECE_TOO_CLOSE'
        if not pieces:
            self.state = 'SEARCH_PIECE'
            return 'LOST_PIECE_WHILE_PUSH'
        # 视觉伺服：保持棋子居中 + 小步前进
        piece = min(pieces, key=lambda p: abs(p['cx'] - self.target_piece['cx']))
        self.target_piece = piece
        err = piece['cx'] - config.IMG_CENTER_X
        if abs(err) > config.SERVO_DEADZONE_PX:
            angle = err * config.SERVO_TURN_KP * 0.5
            self.comm.cmd_turn(angle)
            self.comm.wait_done('TURN', timeout_ms=800)
        self.comm.cmd_move(config.MOVE_STEP_MM)
        self.comm.wait_done('MOVE', timeout_ms=2000)
        return f'PUSH area={piece["area"]}'

    # ---------- 状态：进球后倒车 ----------
    def _do_score(self):
        self.comm.cmd_stop()
        time.sleep_ms(200)
        self.comm.cmd_move(-60)  # 倒车 60mm
        self.comm.wait_done('MOVE', timeout_ms=2000)
        self.state = 'SEARCH_GOAL'
        return 'SCORED_AND_REVERSE'

    # ---------- 辅助：判断棋子与球门是否重叠 ----------
    def _is_goal_overlap(self, piece, goal):
        # 矩形重叠检测
        px1, py1 = piece['x'], piece['y']
        px2, py2 = piece['x'] + piece['w'], piece['y'] + piece['h']
        gx1, gy1 = goal['x'], goal['y']
        gx2, gy2 = goal['x'] + goal['w'], goal['y'] + goal['h']
        ix1 = max(px1, gx1)
        iy1 = max(py1, gy1)
        ix2 = min(px2, gx2)
        iy2 = min(py2, gy2)
        if ix2 <= ix1 or iy2 <= iy1:
            return False
        overlap_area = (ix2 - ix1) * (iy2 - iy1)
        piece_area = piece['w'] * piece['h']
        return piece_area > 0 and (overlap_area / piece_area) > config.GOAL_OVERLAP_RATIO
