"""
象棋棋子模板图批量生成工具
==========================
功能：把手机拍的棋子照片，批量处理成 K230 vision_ocr.py 能用的 .pgm 模板图。

依赖：pip install pillow

使用步骤：
1. 用手机拍每个棋子的清晰正面照（光线均匀，汉字居中）
2. 把照片放到 photos/ 文件夹，按棋子类型命名：
     red_shuai.jpg   （红帅）
     red_che.jpg     （红车）
     red_ma.jpg      （红马）
     red_pao.jpg     （红炮）
     red_xiang.jpg   （红相）
     red_shi.jpg     （红仕）
     red_bing.jpg    （红兵）
     black_jiang.jpg （黑将）
     black_che.jpg   （黑车）
     black_ma.jpg    （黑马）
     black_pao.jpg   （黑炮）
     black_xiang.jpg （黑象）
     black_shi.jpg   （黑士）
     black_zu.jpg    （黑卒）
   （支持 .jpg / .jpeg / .png 格式）
3. 运行：python make_templates.py
4. 生成的 .pgm 模板在 output/ 文件夹，全部上传到 K230 的 /sdcard/templates/
"""

import os
import sys
from PIL import Image, ImageOps, ImageFilter

# ============ 配置 ============
INPUT_DIR = 'photos'          # 输入照片文件夹
OUTPUT_DIR = 'output'         # 输出模板文件夹
TEMPLATE_SIZE = 48            # 模板尺寸（48x48）
CENTER_CROP_RATIO = 0.6       # 从中心裁出多少比例的区域（0.6=中心60%）
BINARY_THRESHOLD = 128        # 二值化阈值（0-255，低于此值=黑，高于=白）
# ==============================


def process_one(input_path, output_path):
    """处理单张照片：裁中心 → 灰度 → 二值化 → 缩放 → 存 .pgm"""
    img = Image.open(input_path)

    # 1. 裁中心区域（去掉棋子外圈，只留汉字）
    w, h = img.size
    crop_w = int(w * CENTER_CROP_RATIO)
    crop_h = int(h * CENTER_CROP_RATIO)
    left = (w - crop_w) // 2
    top = (h - crop_h) // 2
    img = img.crop((left, top, left + crop_w, top + crop_h))

    # 2. 转灰度
    img = img.convert('L')

    # 3. 轻度模糊去噪
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # 4. 二值化（汉字深色→黑，棋子底色浅→白）
    img = img.point(lambda x: 0 if x < BINARY_THRESHOLD else 255, '1')

    # 5. 缩放到统一尺寸
    img = img.resize((TEMPLATE_SIZE, TEMPLATE_SIZE), Image.LANCZOS)
    # resize 后转回二值
    img = img.point(lambda x: 0 if x < 128 else 255, '1')

    # 6. 存 .pgm（MaixPy 支持的灰度图格式）
    img.convert('L').save(output_path)
    print(f'  生成: {output_path}  ({TEMPLATE_SIZE}x{TEMPLATE_SIZE})')


def main():
    if not os.path.isdir(INPUT_DIR):
        os.makedirs(INPUT_DIR, exist_ok=True)
        print(f'已创建输入文件夹: {INPUT_DIR}/')
        print('请把棋子照片按命名规范放入后重新运行。')
        sys.exit(0)

    if not os.path.isdir(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 支持的扩展名
    exts = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(exts)]

    if not files:
        print(f'{INPUT_DIR}/ 文件夹是空的，请放入棋子照片。')
        sys.exit(0)

    # 合法的棋子类型名
    valid_types = {
        'red_shuai', 'red_che', 'red_ma', 'red_pao', 'red_xiang', 'red_shi', 'red_bing',
        'black_jiang', 'black_che', 'black_ma', 'black_pao', 'black_xiang', 'black_shi', 'black_zu',
    }

    print(f'找到 {len(files)} 张照片，开始处理...\n')

    ok_count = 0
    for fname in sorted(files):
        name = os.path.splitext(fname)[0]
        if name not in valid_types:
            print(f'  ⚠️  跳过 {fname}（文件名不是合法的棋子类型）')
            print(f'      合法命名: {sorted(valid_types)}')
            continue
        in_path = os.path.join(INPUT_DIR, fname)
        out_path = os.path.join(OUTPUT_DIR, name + '.pgm')
        try:
            process_one(in_path, out_path)
            ok_count += 1
        except Exception as e:
            print(f'  ❌ 处理失败 {fname}: {e}')

    print(f'\n完成：成功生成 {ok_count} 个模板 → {OUTPUT_DIR}/')
    print('\n下一步：把 output/ 里所有 .pgm 文件上传到 K230 的 /sdcard/templates/ 目录')


if __name__ == '__main__':
    main()
