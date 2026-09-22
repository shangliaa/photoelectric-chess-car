# motion.py — 高层运动控制
# 提供：前进指定距离、转向指定角度、航迹推算、避障
# 非阻塞设计：update() 在主循环周期调用，move_distance/turn_angle 分步执行

import math
import time
import config
from motor import DualMotor
from imu import MPU6050
from vl53l0x import DualRanging

PULSES_PER_MM = config.PULSES_PER_REV / (math.pi * config.WHEEL_DIAMETER_MM)


class MotionController:
    def __init__(self, i2c):
        self.motors = DualMotor()
        self.imu = MPU6050(i2c)
        self.imu.calibrate()
        self.ranging = DualRanging(i2c)
        # 航迹推算
        self.x = 0.0
        self.y = 0.0
        self._last_enc_l = self.motors.enc_l.count
        self._last_enc_r = self.motors.enc_r.count
        # 运动状态
        self._state = 'idle'   # idle / moving / turning
        self._target_dist_mm = 0.0
        self._target_angle = 0.0
        self._speed_pct = 0
        self._start_heading = 0.0
        self.obstacle = False

    # ---------- 航迹推算 ----------
    def update_odometry(self):
        cl = self.motors.enc_l.count
        cr = self.motors.enc_r.count
        dl = (cl - self._last_enc_l) / PULSES_PER_MM
        dr = (cr - self._last_enc_r) / PULSES_PER_MM
        self._last_enc_l = cl
        self._last_enc_r = cr
        d_center = (dl + dr) / 2.0
        # 用 IMU 航向做航迹推算
        heading_rad = math.radians(self.imu.heading)
        self.x += d_center * math.cos(heading_rad)
        self.y += d_center * math.sin(heading_rad)

    def get_pose(self):
        return self.x, self.y, self.imu.heading

    # ---------- 运动指令 ----------
    def move_distance(self, dist_mm, speed_pct=None):
        """前进 dist_mm（负=后退）。非阻塞，需周期调用 update()。"""
        if speed_pct is None:
            speed_pct = config.MOVE_SPEED_PCT
        self._state = 'moving'
        self._target_dist_mm = dist_mm
        self._speed_pct = speed_pct
        self._start_heading = self.imu.heading
        self._start_enc_l = self.motors.enc_l.count
        self._start_enc_r = self.motors.enc_r.count

    def turn_angle(self, angle_deg, speed_pct=None):
        """原地转向 angle_deg（正=顺时针右转）。非阻塞。"""
        if speed_pct is None:
            speed_pct = config.TURN_SPEED_PCT
        self._state = 'turning'
        self._target_angle = angle_deg
        self._speed_pct = speed_pct
        self._start_heading = self.imu.heading

    def stop(self):
        self._state = 'idle'
        self.motors.stop()

    def is_busy(self):
        return self._state != 'idle'

    # ---------- 周期更新 ----------
    def update(self):
        # IMU 航向更新
        self.imu.update_heading()
        # 电机 PID
        self.motors.update()
        # 航迹推算
        self.update_odometry()

        if self._state == 'moving':
            # 避障检测
            self._check_obstacle()
            if self.obstacle:
                self.stop()
                return
            # 计算已走距离
            cl = self.motors.enc_l.count
            cr = self.motors.enc_r.count
            dl = (cl - self._start_enc_l) / PULSES_PER_MM
            dr = (cr - self._start_enc_r) / PULSES_PER_MM
            traveled = (dl + dr) / 2.0
            if abs(traveled) >= abs(self._target_dist_mm):
                self.stop()
                return
            # 航向保持：用 IMU 与起始航向偏差做差速修正
            heading_err = self._imu_norm_angle(self.imu.heading - self._start_heading)
            corr = heading_err * 2.0  # 修正系数
            s = self._speed_pct if self._target_dist_mm > 0 else -self._speed_pct
            self.motors.set_speeds(s - corr, s + corr)

        elif self._state == 'turning':
            # IMU 航向闭环转向
            err = self._imu_norm_angle(
                (self._start_heading + self._target_angle) - self.imu.heading)
            if abs(err) < config.TURN_DEADZONE_DEG:
                self.stop()
                return
            # 差速：右转（正）时左轮正、右轮负
            direction = 1.0 if err > 0 else -1.0
            speed = min(self._speed_pct, abs(err) * 1.5)
            self.motors.set_speeds(direction * speed, -direction * speed)

    def _check_obstacle(self):
        l, r = self.ranging.read()
        if (l > 0 and l < config.OBSTACLE_THRESHOLD_MM) or \
           (r > 0 and r < config.OBSTACLE_THRESHOLD_MM):
            self.obstacle = True
        else:
            self.obstacle = False

    @staticmethod
    def _imu_norm_angle(a):
        while a > 180:
            a -= 360
        while a < -180:
            a += 360
        return a
