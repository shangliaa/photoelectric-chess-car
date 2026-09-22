# encoder.py — AB 相光电编码器驱动（4 倍频计数，带方向）
# 使用 Pin 外部中断，适用于中低速（推棋场景 PWM≤60 足够）

from machine import Pin


class Encoder:
    """AB 相增量编码器，4 倍频解码。"""

    def __init__(self, pin_a, pin_b):
        self._a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self._b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self._count = 0
        # 4 倍频状态表：根据 (oldA,oldB,newA,newB) 决定方向
        self._state = (self._a.value(), self._b.value())
        # 同时监听 A、B 的上升沿和下降沿
        self._a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq)
        self._b.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq)

    def _irq(self, pin):
        new_state = (self._a.value(), self._b.value())
        old = self._state
        # 状态变化表（顺时针 +1，逆时针 -1，无效跳变 0）
        if old == (0, 0):
            if new_state == (0, 1):
                self._count -= 1
            elif new_state == (1, 0):
                self._count += 1
        elif old == (0, 1):
            if new_state == (1, 1):
                self._count -= 1
            elif new_state == (0, 0):
                self._count += 1
        elif old == (1, 1):
            if new_state == (1, 0):
                self._count -= 1
            elif new_state == (0, 1):
                self._count += 1
        elif old == (1, 0):
            if new_state == (0, 0):
                self._count -= 1
            elif new_state == (1, 1):
                self._count += 1
        self._state = new_state

    @property
    def count(self):
        return self._count

    def reset(self):
        self._count = 0

    def read_and_reset(self):
        c = self._count
        self._count = 0
        return c


# ---- 单元测试：上电后手动转动轮子，串口观察脉冲数 ----
if __name__ == '__main__':
    import time
    from config import PIN_ENCODER_L_A, PIN_ENCODER_L_B, PIN_ENCODER_R_A, PIN_ENCODER_R_B
    enc_l = Encoder(PIN_ENCODER_L_A, PIN_ENCODER_L_B)
    enc_r = Encoder(PIN_ENCODER_R_A, PIN_ENCODER_R_B)
    print('编码器测试：转动左右轮观察脉冲数（正转+ / 反转-）')
    while True:
        print(f'L={enc_l.count:>8d}  R={enc_r.count:>8d}')
        time.sleep_ms(200)
