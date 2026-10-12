# vision_ocr.py — 象棋棋子字符识别（模板匹配法）
# 基于 K230 MaixPy 的 image.find_template（归一化互相关 NCC）
# 用途：在颜色色块找到棋子后，进一步识别棋子上的汉字（帅/将/车/马/炮/相/士/兵/卒），
#       从而获得棋子分值，供策略层优先选择高分目标。
#
# 使用方法：
#   1. 把每个棋子字符的模板图（.pgm 或 .bmp）放到 K230 的 /sdcard/templates/ 目录
#      模板命名：red_shuai.pgm, red_che.pgm, ..., black_jiang.pgm 等
#      模板图制作：对着棋子拍清晰照片，裁出汉字区域，转成灰度图，缩放至统一尺寸（如 48x48）
#   2. 调用 recognize_piece(img, blob) 即可返回棋子类型、分值、置信度
#
# 备选：若不想做模板图，可改用 KPU 神经网络（需训练 14 分类模型），见文末注释。

import time
import os
import image  # MaixPy image 模块
import config


class PieceOCR:
    """象棋棋子字符识别器。"""

    def __init__(self):
        self.templates = {}       # {棋子类型: 模板图像对象}
        self._load_templates()

    # ---------- 模板加载 ----------
    def _load_templates(self):
        """从 /sdcard/templates/ 加载所有 .pgm 模板。"""
        template_dir = '/sdcard/templates'
        try:
            files = os.listdir(template_dir)
        except OSError:
            print('[OCR] 模板目录不存在，识字功能不可用')
            return
        for fname in files:
            if not fname.endswith('.pgm'):
                continue
            piece_type = fname[:-4]   # 去掉 .pgm
            try:
                path = f'{template_dir}/{fname}'
                self.templates[piece_type] = image.Image(path)
                print(f'[OCR] 加载模板: {piece_type}')
            except Exception as e:
                print(f'[OCR] 加载失败 {fname}: {e}')
        print(f'[OCR] 共加载 {len(self.templates)} 个模板')

    @property
    def available(self):
        return len(self.templates) > 0

    # ---------- 棋子区域裁剪与预处理 ----------
    def crop_piece(self, img, blob):
        """从原图中裁出棋子区域，返回灰度图（用于匹配）。

        blob 格式：{'x', 'y', 'w', 'h', 'cx', 'cy', 'area'}
        """
        x, y, w, h = blob['x'], blob['y'], blob['w'], blob['h']
        # 向中心收缩一点，去掉棋子边缘的圆形背景
        margin = int(min(w, h) * 0.15)
        x += margin
        y += margin
        w -= margin * 2
        h -= margin * 2
        if w < 16 or h < 16:
            return None
        # 裁剪并转灰度
        piece_img = img.copy((x, y, w, h))
        piece_img = piece_img.to_grayscale()
        # 二值化：汉字是深色，棋子底色浅
        piece_img = piece_img.binary([(0, 100)])   # 阈值按实际调整
        return piece_img

    # ---------- 核心识别 ----------
    def recognize(self, img, blob):
        """识别单个棋子，返回 (棋子类型, 分值, 置信度)。

        若无模板或识别失败，返回 (None, 0, 0.0)。
        """
        if not self.available:
            return None, 0, 0.0

        piece_img = self.crop_piece(img, blob)
        if piece_img is None:
            return None, 0, 0.0

        best_type = None
        best_score = 0.0
        for piece_type, tpl in self.templates.items():
            # find_template 返回 (匹配得分, x, y)，得分越高越相似
            result = piece_img.find_template(tpl, threshold=0.5)
            if result:
                score = result[0]
                if score > best_score:
                    best_score = score
                    best_type = piece_type

        if best_type is None or best_score < config.OCR_MIN_CONFIDENCE:
            return None, 0, best_score

        value = config.PIECE_VALUES.get(best_type, 0)
        return best_type, value, best_score

    def recognize_all(self, img, blobs):
        """批量识别多个棋子，返回 [{blob, type, value, confidence}, ...]。"""
        results = []
        for blob in blobs:
            ptype, value, conf = self.recognize(img, blob)
            results.append({
                'blob': blob,
                'type': ptype,
                'value': value,
                'confidence': conf,
            })
        return results


# ============================================================
# 备选方案：KPU 神经网络识字（更高精度，需提前训练）
# ============================================================
# 若模板匹配在赛场光照下不稳定，可改用 KPU CNN：
#
# 1. 采集数据：每个棋子类型拍 50-100 张，标注类型
# 2. 训练模型：用 Keras/PyTorch 训一个 14 分类小 CNN（输入 48x48x1）
# 3. 转换模型：用 nncase 把 .h5/.onnx 转成 K230 的 .kmodel
# 4. 部署推理：
#
#   from maix import nn
#   model = nn.load('/sdcard/piece_ocr.kmodel')
#   piece_img = crop_piece(img, blob).resize(48, 48)
#   output = model.forward(piece_img)
#   idx = output.index(max(output))
#   piece_type = CLASS_NAMES[idx]
#
# 模板匹配 vs KPU CNN：
#   - 模板匹配：零训练成本，光照/角度变化大时精度下降
#   - KPU CNN：需要数据+训练，但对光照/角度鲁棒，适合正式比赛
# ============================================================
