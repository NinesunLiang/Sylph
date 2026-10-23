import 'package:opencv_dart/opencv_dart.dart' as cv;
import 'package:image/image.dart' as img;

import '../coach/suggestion.dart' show Rect01;
import 'face_detector.dart' show FaceDetection;

/// YuNet 人脸检测原生后端（opencv_dart 2.2.2 / dartcv4）。
///
/// 实现 [FaceDetector.nativeBackend] 的插座：给一张 [img.Image]，
/// 返回 [FaceDetection]（找不到 = null，[FaceDetector] 自动落启发式）。
///
/// ## 诚实边界
/// - 模型文件（`assets/models/face_detection_yunet_2023mar.onnx`）
///   由调用方传入路径；加载失败 → 抛异常，[FaceDetector] 捕获后静默降级。
/// - 检测不到脸 → 返回 null（**不编框**）。
/// - opencv_dart 原生库构建失败（缺 cmake / 缺模块）→ 构造时抛，
///   同样被 [FaceDetector] 捕获降级。
///
/// ## 红线
/// 不用 ML Kit / google_mlkit（华为无 GMS 会崩，`tool/check_no_google.sh`）。
/// YuNet 走 opencv_dart 纯原生，不碰红线。

class YunetBackend {
  YunetBackend({
    required this.modelPath,
    this.inputSize = 320,
    this.scoreThreshold = 0.65,
  });

  /// 模型文件路径（asset 或绝对路径）。
  final String modelPath;

  /// 模型输入边长（YuNet 默认 320×320）。
  final int inputSize;

  /// 置信度门槛（低于此 = 不信，返回 null）。
  final double scoreThreshold;

  cv.Net? _net;
  bool _loaded = false;

  /// 惰性加载模型（第一次 detect 时）。
  /// 加载失败抛异常，由 [FaceDetector] 捕获降级。
  void _ensureLoaded() {
    if (_loaded) return;
    _net = cv.Net.fromOnnx(modelPath);
    _loaded = true;
  }

  /// 检测一张图。返回 null = 没找到（FaceDetector 会落启发式）。
  /// 加载/运行失败抛异常，由 FaceDetector 捕获。
  FaceDetection? detect(img.Image image) {
    if (image.width > 1280) {
      final scale = 1280.0 / image.width;
      image = img.copyResize(
        image,
        width: (image.width * scale).round(),
        height: (image.height * scale).round(),
      );
    }
    _ensureLoaded();
    final net = _net!;

    final src = _toMat(image);
    final resized = cv.resize(src, (inputSize, inputSize));
    final blob = cv.blobFromImage(
      resized,
      scalefactor: 1.0 / 127.5,
      size: (inputSize, inputSize),
      mean: cv.Scalar(127.5, 127.5, 127.5, 0),
      swapRB: true,
    );

    try {
      net.setInput(blob);
      final out = net.forward();

      // YuNet 输出: N × 15（N = 检测数，每行 15 个 float32）
      // 字段: [x, y, w, h, score, ...]（像素坐标，相对 inputSize）
      final n = out.rows;
      final per = out.cols;
      if (n <= 0 || per < 5) return null;

      var best = -1.0;
      var bx = 0.0, by = 0.0, bw = 0.0, bh = 0.0;

      for (var i = 0; i < n; i++) {
        final score = out.at<double>(i, 4);
        if (score < scoreThreshold) continue;
        if (score > best) {
          best = score;
          bx = out.at<double>(i, 0) / inputSize;
          by = out.at<double>(i, 1) / inputSize;
          bw = out.at<double>(i, 2) / inputSize;
          bh = out.at<double>(i, 3) / inputSize;
        }
      }

      if (best < scoreThreshold) return null;

      const pad = 0.10;
      final l = (bx - bw * pad).clamp(0.0, 1.0);
      final t = (by - bh * pad).clamp(0.0, 1.0);
      final w = (bw * (1 + 2 * pad)).clamp(0.0, 1.0 - l);
      final h = (bh * (1 + 2 * pad)).clamp(0.0, 1.0 - t);

      return FaceDetection(
        found: true,
        box: Rect01(l, t, w, h),
        confidence: best.clamp(0.0, 1.0),
        reason: 'YuNet 原生检测（置信度 ${(best * 100).toStringAsFixed(0)}%）',
        source: 'yunet',
      );
    } finally {
      src.dispose();
      resized.dispose();
      blob.dispose();
    }
  }

  /// 释放原生资源。
  void dispose() {
    _net?.dispose();
    _net = null;
    _loaded = false;
  }
}

/// img.Image (RGB/RGBA) → cv.Mat (BGR, 8UC3)。
cv.Mat _toMat(img.Image image) {
  final w = image.width;
  final h = image.height;
  final mat = cv.Mat.create(rows: h, cols: w, type: cv.MatType.CV_8UC3);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final px = image.getPixel(x, y);
      final r = px[0];
      final g = px.length > 1 ? px[1] : r;
      final b = px.length > 2 ? px[2] : r;
      mat.setU8(y * w + x, b as int, i1: 0);
      mat.setU8(y * w + x, g as int, i1: 1);
      mat.setU8(y * w + x, r as int, i1: 2);
    }
  }
  return mat;
}
