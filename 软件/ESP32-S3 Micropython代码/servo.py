# servo.py — SG90M 数字舵机控制（50Hz PWM，角度 0-180°）

from machine import Pin, PWM
import config


class Servo:
    """单个舵机，角度 0~180 度。"""

    def __init__(self, pin, min_angle=0, max_angle=180):
        self._pwm = PWM(Pin(pin), freq=50)
        self._min = min_angle
        self._max = max_angle
        self._angle = 90
        self.set_angle(90)

    def set_angle(self, angle):
        angle = max(self._min, min(self._max, angle))
        self._angle = angle
        # SG90: 0.5ms~2.5ms 对应 0~180°，周期 20ms
        # duty = (0.5 + angle/180 * 2.0) / 20 * 1023
        duty = int((0.5 + angle / 180.0 * 2.0) / 20.0 * 1023)
        self._pwm.duty(duty)

    def get_angle(self):
        return self._angle


class Gimbal:
    """二自由度云台：pan 水平，tilt 俯仰。"""

    def __init__(self):
        self.pan = Servo(config.PIN_SERVO_PAN, config.SERVO_PAN_MIN, config.SERVO_PAN_MAX)
        self.tilt = Servo(config.PIN_SERVO_TILT, config.SERVO_TILT_MIN, config.SERVO_TILT_MAX)
        self.center()

    def center(self):
        self.pan.set_angle(config.SERVO_PAN_CENTER)
        self.tilt.set_angle(config.SERVO_TILT_CENTER)

    def set(self, pan, tilt):
        self.pan.set_angle(pan)
        self.tilt.set_angle(tilt)


# ---- 单元测试：云台居中 -> 左右扫 -> 居中 ----
if __name__ == '__main__':
    import time
    gimbal = Gimbal()
    time.sleep(1)
    for a in range(30, 151, 30):
        gimbal.pan.set_angle(a)
        time.sleep_ms(400)
    gimbal.center()
    print('舵机测试完成')
