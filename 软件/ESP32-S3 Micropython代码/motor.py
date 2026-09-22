# motor.py — TB6612FNG 电机驱动 + 单轮速度 PID 闭环
# 用法：
#   m = Motor(pwm_pin, in1, in2, encoder, stby_pin)
#   m.set_speed(50)   # 目标速度占空比 -100~100（负=反转），内部 PID 闭环

from machine import Pin, PWM
from encoder import Encoder
import time
import config


class PID:
    """增量式速度 PID。"""

    def __init__(self, kp, ki, kd, out_min=-1000, out_max=1000):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.out_min = out_min
        self.out_max = out_max
        self._prev_err = 0
        self._integral = 0

    def reset(self):
        self._prev_err = 0
        self._integral = 0

    def compute(self, setpoint, measurement):
        err = setpoint - measurement
        self._integral += err
        # 积分限幅，防止饱和
        self._integral = max(-5000, min(5000, self._integral))
        deriv = err - self._prev_err
        self._prev_err = err
        out = self.kp * err + self.ki * self._integral + self.kd * deriv
        return max(self.out_min, min(self.out_max, out))


class Motor:
    """单路电机：PWM 调速 + 方向 + 编码器速度闭环。"""

    def __init__(self, pwm_pin, in1_pin, in2_pin, encoder: Encoder, stby_pin=None):
        self._pwm = PWM(Pin(pwm_pin), freq=20000)
        self._in1 = Pin(in1_pin, Pin.OUT)
        self._in2 = Pin(in2_pin, Pin.OUT)
        if stby_pin is not None:
            self._stby = Pin(stby_pin, Pin.OUT)
            self._stby.value(1)  # 使能驱动
        else:
            self._stby = None
        self._enc = encoder
        self._pid = PID(config.MOTOR_KP, config.MOTOR_KI, config.MOTOR_KD,
                        out_min=-config.MOTOR_PWM_MAX, out_max=config.MOTOR_PWM_MAX)
        self._target_speed = 0.0   # 目标速度（脉冲/周期），0=停止
        self._prev_count = encoder.count
        self._last_time = time.ticks_ms()

    def set_duty(self, duty):
        """直接设置 PWM 占空比（-1000~1000），无闭环，用于调试。"""
        duty = int(max(-config.MOTOR_PWM_MAX, min(config.MOTOR_PWM_MAX, duty)))
        if duty >= 0:
            self._in1.value(1)
            self._in2.value(0)
        else:
            self._in1.value(0)
            self._in2.value(1)
            duty = -duty
        self._pwm.duty(duty)

    def set_speed(self, speed_pct):
        """设置目标速度占空比 -100~100，内部转成脉冲/周期并 PID 闭环。"""
        # speed_pct 为占空比百分比；目标脉冲数 = 占空比/100 * 最大脉冲数
        # 这里用一个经验系数，把百分比映射到每周期目标脉冲
        max_pulse = 300.0  # 全速时每 20ms 脉冲数（按实际电机调整）
        self._target_speed = speed_pct / 100.0 * max_pulse

    def stop(self):
        self._target_speed = 0.0
        self._pid.reset()
        self.set_duty(0)

    def update(self):
        """每个 PID 周期调用一次：计算实际速度 -> PID -> 输出 PWM。"""
        now = time.ticks_ms()
        dt = time.ticks_diff(now, self._last_time)
        if dt < config.MOTOR_PID_INTERVAL_MS:
            return
        self._last_time = now
        cur = self._enc.count
        speed = cur - self._prev_count  # 脉冲数/周期
        self._prev_count = cur
        if self._target_speed == 0:
            self.set_duty(0)
            return
        output = self._pid.compute(self._target_speed, speed)
        self.set_duty(output)


class DualMotor:
    """双轮差速封装。"""

    def __init__(self):
        self.enc_l = Encoder(config.PIN_ENCODER_L_A, config.PIN_ENCODER_L_B)
        self.enc_r = Encoder(config.PIN_ENCODER_R_A, config.PIN_ENCODER_R_B)
        self.left = Motor(config.PIN_MOTOR_L_PWM, config.PIN_MOTOR_L_IN1,
                          config.PIN_MOTOR_L_IN2, self.enc_l, config.PIN_MOTOR_STBY)
        self.right = Motor(config.PIN_MOTOR_R_PWM, config.PIN_MOTOR_R_IN1,
                           config.PIN_MOTOR_R_IN2, self.enc_r, config.PIN_MOTOR_STBY)

    def set_speeds(self, left_pct, right_pct):
        self.left.set_speed(left_pct)
        self.right.set_speed(right_pct)

    def stop(self):
        self.left.stop()
        self.right.stop()

    def update(self):
        self.left.update()
        self.right.update()


# ---- 单元测试：左右轮分别正反转，串口观察编码器脉冲跟随 ----
if __name__ == '__main__':
    import time
    dm = DualMotor()
    print('电机测试：L=50, R=50 前进2秒 -> 停止')
    dm.set_speeds(50, 50)
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 2000:
        dm.update()
        time.sleep_ms(5)
    dm.stop()
    time.sleep_ms(500)
    print(f'脉冲 L={dm.enc_l.count} R={dm.enc_r.count}')
    print('左转差速2秒')
    dm.set_speeds(-30, 30)
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 2000:
        dm.update()
        time.sleep_ms(5)
    dm.stop()
