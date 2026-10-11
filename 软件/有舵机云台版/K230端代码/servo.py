# servo.py — K230 直接控制 SG90M 数字舵机（50Hz PWM）
# 舵机接 K230 散热片旁 12pin 排针：GPIO42(PWM0)=水平, GPIO43(PWM1)=俯仰
# K230 PWM API: from machine import PWM; PWM(pin, freq=50, duty=百分比0~100)

from machine import PWM
import config


class Servo:
    """单个 SG90 舵机，角度 0~180 度。"""

    def __init__(self, pin, min_angle=0, max_angle=180):
        # SG90: 0.5ms~2.5ms 对应 0~180°，周期 20ms(50Hz)
        # duty 百分比 = 脉冲宽度(ms) / 20 * 100
        self._pwm = PWM(pin, freq=50, duty=7.5)  # 默认居中 1.5ms
        self._min = min_angle
        self._max = max_angle
        self._angle = 90
        self.set_angle(90)

    def set_angle(self, angle):
        angle = max(self._min, min(self._max, angle))
        self._angle = angle
        # duty(%) = (0.5 + angle/180 * 2.0) / 20 * 100
        duty = (0.5 + angle / 180.0 * 2.0) / 20.0 * 100
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
