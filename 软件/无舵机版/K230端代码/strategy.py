# strategy.py — 目标选择 + 视觉伺服闭环（无舵机版，非阻塞流畅版）
# 状态机：找球门 -> 找己方棋子 -> 对准 -> 推进 -> 进球倒车 -> 循环
# 本版无云台：找球门靠小车原地步进旋转扫描
# 优化：去掉所有 wait_done 阻塞，发指令后立即返回，靠视觉反馈判断到位，画面流畅

import time
import config
from vision import Vision
from uart_comm import UartComm
from vision_ocr import PieceOCR


class Strategy:
    def __init__(self, vision: Vision, comm: UartComm):
        self.vision = vision
        self.comm = comm
        self.ocr = PieceOCR()                # 棋子字符识别器
        self.state = 'SEARCH_GOAL'   # SEARCH_GOAL / SEARCH_PIECE / ALIGN / PUSH / SCORE
        self.target_piece = None
        self.target_value = 0         # 当前目标棋子的分值
        self.goal = None
        self.goal_cx = config.IMG_CENTER_X
        # 非阻塞控制：指令冷却，避免每帧重复发送
        self._cmd_interval = 300      # 两次指令间隔(ms)，小于此值不发新指令
        self._last_cmd_ms = 0
        # SCORE 状态分阶段计时
        self._score_phase = 0         # 0=停车 1=倒车中
        self._score_start_ms = 0

    def _can_send(self):
        """距上次发指令是否超过冷却时间。"""
        return time.ticks_diff(time.ticks_ms(), self._last_cmd_ms) >= self._cmd_interval

    def _sent(self):
        """标记已发指令。"""
        self._last_cmd_ms = time.ticks_ms()

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

    # ---------- 状态：找球门（无云台：原地旋转扫描） ----------
    def _do_search_goal(self, img):
        if self.goal:
            # 球门已找到，转向使其居中
            err = self.goal['cx'] - config.IMG_CENTER_X
            if abs(err) < config.SERVO_DEADZONE_PX:
                self.state = 'SEARCH_PIECE'
                return 'GOAL_CENTERED'
            if self._can_send():
                angle = err * config.SERVO_TURN_KP
                self.comm.cmd_turn(angle)
                self._sent()
            return f'TURN_TO_GOAL err={err:.0f}'
        else:
            # 球门未找到：小车原地步进旋转扫描
            if self._can_send():
                self.comm.cmd_turn(config.SCAN_TURN_STEP)
                self._sent()
            return 'ROTATING_SCAN'

    # ---------- 状态：找棋子 ----------
    def _do_search_piece(self, img, pieces):
        if not pieces:
            # 没找到棋子，小角度转头继续找
            if self._can_send():
                self.comm.cmd_turn(30)
                self._sent()
            return 'NO_PIECE_TURN'

        # 用 OCR 识别每个棋子的字符和分值，优先选高分棋子
        if self.ocr.available:
            recognized = self.ocr.recognize_all(img, pieces)
            known = [r for r in recognized if r['value'] > 0]
            if known:
                known.sort(key=lambda r: (-r['value'],
                                          abs(r['blob']['cx'] - config.IMG_CENTER_X)))
                best = known[0]
                self.target_piece = best['blob']
                self.target_value = best['value']
                self.state = 'ALIGN'
                return f'FOUND_PIECE type={best["type"]} val={best["value"]}'
            self.target_piece = min(pieces, key=lambda p: abs(p['cx'] - config.IMG_CENTER_X))
            self.target_value = 0
            self.state = 'ALIGN'
            return 'FOUND_PIECE(unknown)'
        else:
            self.target_piece = min(pieces, key=lambda p: abs(p['cx'] - config.IMG_CENTER_X))
            self.target_value = 0
            self.state = 'ALIGN'
            return 'FOUND_PIECE'

    # ---------- 状态：对准棋子 ----------
    def _do_align(self, img, pieces):
        if pieces:
            self.target_piece = min(pieces, key=lambda p: abs(p['cx'] - self.target_piece['cx']))
            err = self.target_piece['cx'] - config.IMG_CENTER_X
            if abs(err) < config.SERVO_DEADZONE_PX:
                self.state = 'PUSH'
                return 'PIECE_ALIGNED'
            if self._can_send():
                angle = err * config.SERVO_TURN_KP
                self.comm.cmd_turn(angle)
                self._sent()
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
                self._score_phase = 0
                return 'GOAL_OVERLAP'
            if piece['area'] > 30000:
                self.state = 'SCORE'
                self._score_phase = 0
                return 'PIECE_TOO_CLOSE'
        if not pieces:
            self.state = 'SEARCH_PIECE'
            return 'LOST_PIECE_WHILE_PUSH'
        # 视觉伺服：保持棋子居中 + 小步前进
        piece = min(pieces, key=lambda p: abs(p['cx'] - self.target_piece['cx']))
        self.target_piece = piece
        err = piece['cx'] - config.IMG_CENTER_X
        if self._can_send():
            if abs(err) > config.SERVO_DEADZONE_PX:
                angle = err * config.SERVO_TURN_KP * 0.5
                self.comm.cmd_turn(angle)
            else:
                self.comm.cmd_move(config.MOVE_STEP_MM)
            self._sent()
        return f'PUSH area={piece["area"]}'

    # ---------- 状态：进球后倒车（分阶段，非阻塞） ----------
    def _do_score(self):
        now = time.ticks_ms()
        if self._score_phase == 0:
            # 阶段0：停车
            self.comm.cmd_stop()
            self._score_start_ms = now
            self._score_phase = 1
            return 'SCORE_STOP'
        elif self._score_phase == 1:
            # 阶段1：等 200ms 后倒车
            if time.ticks_diff(now, self._score_start_ms) > 200:
                self.comm.cmd_move(-60)
                self._score_start_ms = now
                self._score_phase = 2
            return 'SCORE_WAIT_REVERSE'
        else:
            # 阶段2：倒车 1.5s 后回搜索状态
            if time.ticks_diff(now, self._score_start_ms) > 1500:
                self.state = 'SEARCH_GOAL'
                return 'SCORED_DONE'
            return 'SCORE_REVERSING'

    # ---------- 辅助：判断棋子与球门是否重叠 ----------
    def _is_goal_overlap(self, piece, goal):
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
