const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
        LevelFormat, PageBreak } = require('docx');

const cjkFont = { ascii: "Arial", hAnsi: "Arial", eastAsia: "Microsoft YaHei" };

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
}
function p(text) {
  return new Paragraph({ children: [new TextRun(text)] });
}
function bullet(text) {
  return new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun(text)] });
}
function code(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: { ascii: "Consolas", hAnsi: "Consolas", eastAsia: "Consolas" }, size: 20 })]
  });
}

// 棋子命名表
const pieces = [
  ["red_shuai", "红帅", "10"],
  ["red_che", "红车", "9"],
  ["red_ma", "红马", "8"],
  ["red_pao", "红炮", "7"],
  ["red_xiang", "红相", "6"],
  ["red_shi", "红仕", "5"],
  ["red_bing", "红兵", "1"],
  ["black_jiang", "黑将", "10"],
  ["black_che", "黑车", "9"],
  ["black_ma", "黑马", "8"],
  ["black_pao", "黑炮", "7"],
  ["black_xiang", "黑象", "6"],
  ["black_shi", "黑士", "5"],
  ["black_zu", "黑卒", "1"],
];

function makePieceTable() {
  const header = new TableRow({
    cantSplit: true,
    children: [
      new TableCell({ borders, width: { size: 3000, type: WidthType.DXA }, shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "文件名", bold: true })] })] }),
      new TableCell({ borders, width: { size: 3000, type: WidthType.DXA }, shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "对应棋子", bold: true })] })] }),
      new TableCell({ borders, width: { size: 3000, type: WidthType.DXA }, shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "分值", bold: true })] })] }),
    ]
  });
  const rows = pieces.map(([name, piece, val]) => new TableRow({
    cantSplit: true,
    children: [
      new TableCell({ borders, width: { size: 3000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: name, font: { ascii: "Consolas", hAnsi: "Consolas" } })] })] }),
      new TableCell({ borders, width: { size: 3000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun(piece)] })] }),
      new TableCell({ borders, width: { size: 3000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun(val)] })] }),
    ]
  }));
  return new Table({ width: { size: 9000, type: WidthType.DXA }, columnWidths: [3000, 3000, 3000], rows: [header, ...rows] });
}

// 支持平台表
function makePlatformTable() {
  const header = new TableRow({
    cantSplit: true,
    children: [
      new TableCell({ borders, width: { size: 2200, type: WidthType.DXA }, shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "平台", bold: true })] })] }),
      new TableCell({ borders, width: { size: 3000, type: WidthType.DXA }, shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "匹配函数", bold: true })] })] }),
      new TableCell({ borders, width: { size: 3800, type: WidthType.DXA }, shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "模板存放路径示例", bold: true })] })] }),
    ]
  });
  const data = [
    ["K230 (MaixPy)", "img.find_template()", "/sdcard/templates/"],
    ["MaixCAM", "img.find_template()", "/root/templates/"],
    ["K210 (MaixPy)", "img.find_template()", "/sdcard/templates/"],
    ["OpenMV", "img.find_template()", "/templates/"],
    ["ESP32-CAM", "自建模板匹配 / TF Lite", "SPIFFS 或 SD 卡"],
    ["树莓派 / PC", "OpenCV cv2.matchTemplate()", "任意本地路径"],
  ];
  const rows = data.map(([plat, func, path]) => new TableRow({
    cantSplit: true,
    children: [
      new TableCell({ borders, width: { size: 2200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun(plat)] })] }),
      new TableCell({ borders, width: { size: 3000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: func, font: { ascii: "Consolas", hAnsi: "Consolas" } })] })] }),
      new TableCell({ borders, width: { size: 3800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: path, font: { ascii: "Consolas", hAnsi: "Consolas" } })] })] }),
    ]
  }));
  return new Table({ width: { size: 9000, type: WidthType.DXA }, columnWidths: [2200, 3000, 3800], rows: [header, ...rows] });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: cjkFont, size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: cjkFont },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0, keepNext: false, keepLines: false } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: cjkFont },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1, keepNext: false, keepLines: false } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children: [
      // 标题
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: "象棋棋子模板图制作工具", size: 44, bold: true, font: cjkFont })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [new TextRun({ text: "通用使用说明", size: 32, font: cjkFont })] }),
      p("本工具用于将手机拍摄的象棋棋子照片，批量处理成嵌入式视觉平台可直接使用的模板图（.pgm 灰度图）。生成的模板可用于模板匹配（NCC）方式的棋子字符识别。"),
      p(""),

      h1("一、适用平台"),
      p("本工具生成的 .pgm 模板图为标准 PGM 灰度图格式，可用于所有支持模板匹配或图像读取的嵌入式视觉平台，包括但不限于："),
      makePlatformTable(),
      p(""),
      p("核心原理：将棋子照片裁出汉字区域、灰度化、二值化、缩放为统一尺寸，供目标设备的 find_template() 或等效匹配函数使用。"),
      p(""),

      h1("二、工作原理"),
      p("工具对每张照片依次执行以下处理："),
      bullet("中心裁剪：裁出照片中心区域，去掉棋子外圈背景"),
      bullet("灰度化：转为单通道灰度图"),
      bullet("中值滤波：去除噪点"),
      bullet("二值化：汉字（深色）转黑，棋子底色（浅色）转白"),
      bullet("缩放：统一缩放到 48×48 像素"),
      bullet("保存为 .pgm 格式"),
      p(""),

      h1("三、使用步骤"),

      h2("3.1 拍摄棋子照片"),
      p("用手机正对每个棋子拍摄一张清晰照片，要求："),
      bullet("光线均匀，避免反光和阴影"),
      bullet("汉字居中、清晰可辨"),
      bullet("背景尽量干净（复杂背景可后期手动裁剪）"),
      bullet("同一批照片保持拍摄距离和角度一致"),
      p(""),

      h2("3.2 命名并放入 photos 文件夹"),
      p("将照片重命名为对应的棋子类型，放入 photos 文件夹。命名规范如下："),
      makePieceTable(),
      p(""),
      p("支持的图片格式：.jpg / .jpeg / .png / .bmp / .webp"),
      p(""),

      h2("3.3 运行脚本"),
      code("cd 模板图制作工具"),
      code("python make_templates.py"),
      p("生成的 .pgm 模板位于 output 文件夹。"),
      p(""),

      h2("3.4 上传到目标设备"),
      p("将 output 文件夹中的所有 .pgm 文件上传到目标设备的模板目录："),
      bullet("K230：/sdcard/templates/"),
      bullet("MaixCAM：/root/templates/"),
      bullet("K210：/sdcard/templates/"),
      bullet("OpenMV：/templates/（内置 Flash 或 SD 卡根目录）"),
      bullet("ESP32-CAM：SPIFFS 或 SD 卡"),
      p(""),

      h1("四、参数调整"),
      p("若生成的模板识别效果不佳，可在 make_templates.py 顶部调整以下参数："),
      new Table({
        width: { size: 9000, type: WidthType.DXA },
        columnWidths: [2500, 1500, 5000],
        rows: [
          new TableRow({ cantSplit: true, children: [
            new TableCell({ borders, width: { size: 2500, type: WidthType.DXA }, shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "参数", bold: true })] })] }),
            new TableCell({ borders, width: { size: 1500, type: WidthType.DXA }, shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "默认值", bold: true })] })] }),
            new TableCell({ borders, width: { size: 5000, type: WidthType.DXA }, shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "说明", bold: true })] })] }),
          ]}),
          ...[
            ["TEMPLATE_SIZE", "48", "模板尺寸（像素），越大越精细但匹配越慢"],
            ["CENTER_CROP_RATIO", "0.6", "从中心裁出的比例（去掉棋子外圈）"],
            ["BINARY_THRESHOLD", "128", "二值化阈值（0-255），低于此值为黑"],
          ].map(([a, b, c]) => new TableRow({ cantSplit: true, children: [
            new TableCell({ borders, width: { size: 2500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: a, font: { ascii: "Consolas", hAnsi: "Consolas" } })] })] }),
            new TableCell({ borders, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun(b)] })] }),
            new TableCell({ borders, width: { size: 5000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun(c)] })] }),
          ]}))
        ]
      }),
      p(""),
      p("调参建议："),
      bullet("汉字偏淡看不清 → 降低 BINARY_THRESHOLD（如 100）"),
      bullet("汉字糊成一团 → 提高 BINARY_THRESHOLD（如 150）"),
      bullet("模板包含棋子外圈 → 降低 CENTER_CROP_RATIO（如 0.5）"),
      bullet("识别精度不够 → 提高 TEMPLATE_SIZE（如 64）"),
      p(""),

      h1("五、各平台识别代码示例"),
      p("以下为各平台加载模板并进行匹配的参考代码。"),

      h2("5.1 K230 / MaixCAM / K210（MaixPy）"),
      code("import image"),
      code("tpl = image.Image('/sdcard/templates/red_shuai.pgm')"),
      code("result = img.find_template(tpl, threshold=0.6)"),
      code("if result:"),
      code("    score = result[0]   # 匹配得分，越高越相似"),
      p(""),

      h2("5.2 OpenMV"),
      code("import sensor, image"),
      code("tpl = image.Image('/templates/red_shuai.pgm')"),
      code("for r in img.find_template(tpl, threshold=0.6):"),
      code("    print('matched', r)"),
      p(""),

      h2("5.3 树莓派 / PC（OpenCV）"),
      code("import cv2"),
      code("tpl = cv2.imread('red_shuai.pgm', 0)"),
      code("res = cv2.matchTemplate(img_gray, tpl, cv2.TM_CCOEFF_NORMED)"),
      code("_, max_val, _, max_loc = cv2.minMaxLoc(res)"),
      code("if max_val > 0.6:"),
      code("    print('matched, score=', max_val)"),
      p(""),

      h1("六、验证模板效果"),
      p("上传模板后运行识别程序，观察识别结果："),
      bullet("识别成功：输出对应棋子类型和分值"),
      bullet("识别失败：检查模板质量，调整二值化阈值或重新拍摄"),
      p("建议先在 PC 上用 OpenCV 测试模板匹配效果，确认无误后再部署到嵌入式设备。"),
      p(""),

      h1("七、进阶：从模板匹配升级到神经网络"),
      p("若赛场光照变化大导致模板匹配精度不足，可改用卷积神经网络（CNN）识别棋子字符："),
      bullet("采集每类棋子 50-100 张照片作为训练数据"),
      bullet("训练 14 分类 CNN 模型（输入 48×48 灰度图）"),
      bullet("K230/K210 用 nncase 转换为 .kmodel，通过 KPU 加速推理"),
      bullet("OpenMV/ESP32-CAM 用 TensorFlow Lite Micro"),
      bullet("树莓派/PC 直接用 ONNX Runtime 或 TFLite"),
      p("模板匹配无需训练、部署简单；CNN 对光照和角度更鲁棒，但需要数据采集和训练。"),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("象棋棋子模板图制作工具-通用使用说明.docx", buffer);
  console.log("文档已生成: 象棋棋子模板图制作工具-通用使用说明.docx");
});
