# vision.py — K230 摄像头采集 + 颜色色块识别
# 基于 K230 MaixPy SDK 的 media.sensor + image.find_blobs（LAB 空间）

import time
from media.sensor import *
from media.display import *
from media.media import *
import config


class Vision:
    def __init__(self):
        self.sensor = None
        self._init_camera()

    def _init_camera(self):
        self.sensor = Sensor()
        self.sensor.reset()
        self.sensor.set_framesize(width=config.IMG_WIDTH, height=config.IMG_HEIGHT)
        self.sensor.set_pixformat(Sensor.RGB565)
        # 显示初始化（LCD/IDE）
        try:
            Display.init(Display.ST7701, to_ide=True)
        except Exception:
            pass  # 无显示也可运行
        MediaManager.init()
        self.sensor.run()
        print('摄像头初始化完成')

    def snapshot(self):
        return self.sensor.snapshot()

    def find_blobs(self, img, threshold, area_min=None, area_max=None):
        """返回符合阈值的色块列表 [x, y, w, h, cx, cy, area]。"""
        if area_min is None:
            area_min = config.BLOB_AREA_MIN
        if area_max is None:
            area_max = config.BLOB_AREA_MAX
        blobs = img.find_blobs([threshold], area_threshold=area_min,
                               pixels_threshold=area_min, merge=True)
        result = []
        for b in blobs:
            if b[2] * b[3] > area_max:
                continue
            # b = (x, y, w, h, pixels, cx, cy)
            result.append({
                'x': b[0], 'y': b[1], 'w': b[2], 'h': b[3],
                'cx': b[5], 'cy': b[6],
                'area': b[4]
            })
        return result

    def find_red_pieces(self, img):
        return self.find_blobs(img, config.RED_THRESHOLD)

    def find_black_pieces(self, img):
        return self.find_blobs(img, config.BLACK_THRESHOLD)

    def find_goal(self, img):
        """返回球门色块（取最大的一个），无则 None。"""
        blobs = self.find_blobs(img, config.GOAL_THRESHOLD)
        if not blobs:
            return None
        return max(blobs, key=lambda b: b['area'])

    def find_my_pieces(self, img):
        """返回己方颜色棋子列表。"""
        if config.MY_COLOR == 'red':
            return self.find_red_pieces(img)
        else:
            return self.find_black_pieces(img)

    def draw_blobs(self, img, blobs, color=(0, 255, 0)):
        """在图像上绘制色块框（调试用）。"""
        for b in blobs:
            img.draw_rectangle((b['x'], b['y'], b['w'], b['h']), color=color, thickness=2)
            img.draw_cross(b['cx'], b['cy'], color=color, thickness=2)

    def deinit(self):
        if self.sensor:
            self.sensor.stop()
        try:
            Display.deinit()
        except Exception:
            pass
        MediaManager.deinit()
