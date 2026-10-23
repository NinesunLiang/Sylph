import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:photo_coach_v2/features/analysis/face_detector.dart';
import 'package:photo_coach_v2/features/analysis/yunet_backend.dart';

/// YuNet 原生后端的单元测试。
///
/// 注意：真正的模型推理需要 opencv_dart 原生库（.so），
/// 在纯 Dart 测试环境（flutter test）里原生库不加载 →
/// 这里只测**接线正确性**（构造、降级行为、参数校验），
/// 不测模型输出（那需要真机/模拟器跑 `flutter run`）。
void main() {
  group('YunetBackend 构造', () {
    test('默认参数', () {
      final b = YunetBackend(modelPath: 'assets/models/face_detection_yunet_2023mar.onnx');
      expect(b.inputSize, 320);
      expect(b.scoreThreshold, 0.65);
    });

    test('自定义参数', () {
      final b = YunetBackend(modelPath: 'x.onnx', inputSize: 640, scoreThreshold: 0.8);
      expect(b.inputSize, 640);
      expect(b.scoreThreshold, 0.8);
    });
  });

  group('降级行为（诚实边界）', () {
    test('模型文件不存在 → detect 抛异常（FaceDetector 会捕获落启发式）', () {
      final b = YunetBackend(modelPath: '/nonexistent/model.onnx');
      final image = img.Image(width: 100, height: 100);
      for (var y = 0; y < 100; y++) {
        for (var x = 0; x < 100; x++) {
          image.setPixelRgb(x, y, 200, 150, 130);
        }
      }
      // 原生库在 flutter test 里不加载 → Net.fromOnnx 会抛
      expect(() => b.detect(image), throwsA(anything));
    });
  });

  group('与 FaceDetector 的接线', () {
    test('FaceDetector（纯启发式）→ 找到脸（不崩）', () async {
      final image = img.Image(width: 200, height: 200);
      for (var y = 0; y < 200; y++) {
        for (var x = 0; x < 200; x++) {
          final inFace = x >= 80 && x < 130 && y >= 70 && y < 130;
          image.setPixelRgb(
            x, y,
            inFace ? 230 : 120,
            inFace ? 180 : 120,
            inFace ? 160 : 120,
          );
        }
      }

      final detector = FaceDetector(
        useIsolate: false,
        nativeBackend: null,
      );
      final bytes = img.encodeJpg(image);
      final result = await detector.detectFromBytes(bytes);

      expect(result.found, isTrue);
      expect(result.source, 'heuristic');
      expect(result.box, isNotNull);
    });
  });
}
