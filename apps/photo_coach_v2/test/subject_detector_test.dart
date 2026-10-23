import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:photo_coach_v2/features/coach/suggestion.dart' show Rect01;
import 'package:photo_coach_v2/features/guidance/alignment.dart';
import 'package:photo_coach_v2/features/guidance/subject_detector.dart';

/// 造一张 RgbGrid：背景一个色，中间一块矩形另一个色。
RgbGrid makeGrid({
  int w = 32,
  int h = 32,
  List<double> bg = const [0.8, 0.8, 0.8],
  List<double> fg = const [0.1, 0.1, 0.1],
  int? boxX,
  int? boxY,
  int? boxW,
  int? boxH,
}) {
  final r = Float32List(w * h);
  final g = Float32List(w * h);
  final b = Float32List(w * h);
  final bx = boxX ?? (w * 0.3).round();
  final by = boxY ?? (h * 0.2).round();
  final bw = boxW ?? (w * 0.4).round();
  final bh = boxH ?? (h * 0.6).round();

  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final inBox = x >= bx && x < bx + bw && y >= by && y < by + bh;
      final c = inBox ? fg : bg;
      final i = y * w + x;
      r[i] = c[0];
      g[i] = c[1];
      b[i] = c[2];
    }
  }
  return RgbGrid(r, g, b, w, h);
}

void main() {
  group('detectSubject —— 本地找主体（F2.12 的基础）', () {
    test('背景浅、中间一块深 → 找到框，位置大致对', () {
      final d = detectSubject(makeGrid(boxX: 10, boxY: 6, boxW: 12, boxH: 20));
      expect(d.found, isTrue);
      expect(d.box, isNotNull);
      // 32x32 网格：x 10..21 → 0.31..0.66；y 6..25 → 0.19..0.81
      expect(d.box!.left, closeTo(10 / 32, 0.06));
      expect(d.box!.top, closeTo(6 / 32, 0.06));
      expect(d.box!.width, closeTo(12 / 32, 0.08));
      expect(d.box!.height, closeTo(20 / 32, 0.08));
      expect(d.confidence, greaterThan(0.2));
      expect(d.coverage, inInclusiveRange(0.05, 0.6));
    });

    test('主体偏左 → box.centerX < 0.5（能指导「往右挪」）', () {
      final d = detectSubject(makeGrid(boxX: 2, boxY: 8, boxW: 8, boxH: 16));
      expect(d.found, isTrue);
      expect(d.box!.centerX, lessThan(0.5));
    });

    test('纯色画面 → 没找到，且不瞎给框', () {
      final d = detectSubject(makeGrid(bg: [0.5, 0.5, 0.5], fg: [0.5, 0.5, 0.5]));
      expect(d.found, isFalse);
      expect(d.box, isNull);
      expect(d.reason, isNotEmpty);
    });

    test('方块太大（占满画面）→ 判为不可信，不给框', () {
      final d = detectSubject(makeGrid(boxX: 0, boxY: 0, boxW: 32, boxH: 32));
      expect(d.found, isFalse);
      expect(d.box, isNull);
    });

    test('方块太小（噪点级）→ 判为不可信，不给框', () {
      final d = detectSubject(
        makeGrid(boxX: 15, boxY: 15, boxW: 1, boxH: 1),
        thresholds: const DetectorThresholds(),
      );
      expect(d.found, isFalse);
      expect(d.box, isNull);
    });

    test('网格太小 → 明确拒绝，不硬算', () {
      final tiny = RgbGrid(
        Float32List(4), Float32List(4), Float32List(4), 2, 2);
      final d = detectSubject(tiny);
      expect(d.found, isFalse);
      expect(d.reason, contains('网格太小'));
    });

    test('颜色差但亮度一样（灰 vs 红）也能认出来', () {
      final d = detectSubject(makeGrid(
        bg: [0.5, 0.5, 0.5],
        fg: [0.8, 0.2, 0.2], // 亮度接近，颜色差很多
        boxX: 8, boxY: 8, boxW: 16, boxH: 16,
      ));
      expect(d.found, isTrue, reason: '色度差应该能补上亮度差');
    });

    test('多个色块 → 取最大那个', () {
      final w = 32, h = 32;
      final r = Float32List(w * h), g = Float32List(w * h), b = Float32List(w * h);
      for (var y = 0; y < h; y++) {
        for (var x = 0; x < w; x++) {
          final i = y * w + x;
          var v = 0.85;
          // 小块（4x4）在左上
          if (x >= 2 && x < 6 && y >= 2 && y < 6) v = 0.1;
          // 大块（8x14）在右侧
          if (x >= 20 && x < 28 && y >= 8 && y < 22) v = 0.1;
          r[i] = v; g[i] = v; b[i] = v;
        }
      }
      final d = detectSubject(RgbGrid(r, g, b, w, h));
      expect(d.found, isTrue);
      expect(d.box!.centerX, greaterThan(0.6), reason: '应该选中右边那个大块');
    });

    test('结果可序列化（要发给 UI / 日志）', () {
      final d = detectSubject(makeGrid());
      expect(d.found, isTrue);
      expect(d.box!.toJson().length, 4);
    });
  });

  group('gridFromImage / gridFromBytes —— 解码 + 缩样', () {
    test('从 img.Image 缩样，长宽比保持', () {
      final image = img.Image(width: 200, height: 100);
      img.fill(image, color: img.ColorRgb8(128, 128, 128));
      final gr = gridFromImage(image, gridW: 48, gridH: 48);
      expect(gr.width, 48);
      expect(gr.height, 24, reason: '200x100 的图缩到宽 48 时高该是 24');
    });

    test('竖图同理', () {
      final image = img.Image(width: 100, height: 200);
      img.fill(image, color: img.ColorRgb8(10, 10, 10));
      final gr = gridFromImage(image, gridW: 48, gridH: 48);
      expect(gr.height, 48);
      expect(gr.width, 24);
    });

    test('像素值归一化到 0–1', () {
      final image = img.Image(width: 8, height: 8);
      img.fill(image, color: img.ColorRgb8(255, 0, 0));
      final gr = gridFromImage(image, gridW: 8, gridH: 8);
      expect(gr.r[0], closeTo(1.0, 0.01));
      expect(gr.g[0], closeTo(0.0, 0.01));
      expect(gr.lumaAt(0), closeTo(0.2126, 0.01));
    });

    test('空字节抛 FormatException', () {
      expect(() => gridFromBytes(Uint8List(0)), throwsA(isA<FormatException>()));
    });

    test('垃圾字节抛 FormatException（不抛底层 RangeError）', () {
      expect(
        () => gridFromBytes(Uint8List.fromList(List.filled(128, 200))),
        throwsA(isA<FormatException>()),
      );
    });

    test('真的 PNG 能解出来', () {
      final image = img.Image(width: 40, height: 40);
      img.fill(image, color: img.ColorRgb8(30, 200, 60));
      final grid = gridFromBytes(Uint8List.fromList(img.encodePng(image)), gridW: 16, gridH: 16);
      expect(grid.width, 16);
      expect(grid.lumaAt(0), closeTo(0.7152 * 200 / 255 + 0.2126 * 30 / 255 + 0.0722 * 60 / 255, 0.02));
    });
  });

  group('compareAlignment —— 实时反馈（讲人话）', () {
    Rect01 r(double l, double t, double w, double h) => Rect01(l, t, w, h);

    test('当前 == 目标 → 保持不动', () {
      final f = compareAlignment(r(0.3, 0.3, 0.2, 0.4), r(0.3, 0.3, 0.2, 0.4));
      expect(f!.aligned, isTrue);
      expect(f.action, AlignAction.stable);
      expect(f.message, contains('保持不动'));
    });

    test('主体偏左、目标偏右 → 镜头要往**左**摇', () {
      final f = compareAlignment(r(0.1, 0.3, 0.2, 0.4), r(0.6, 0.3, 0.2, 0.4));
      expect(f!.aligned, isFalse);
      // ⚠️ 提示说的是**相机动作**（label 是「相机往上抬一点」这种口吻）。
      // 要让主体在画面里往右走，相机必须往**左**摇 —— 相机往右摇会把主体推更左。
      expect(f.action, AlignAction.moveLeft);
      expect(f.message, contains('向左移'));
      expect(f.dx, greaterThan(0));
    });

    test('主体偏右、目标偏左 → 镜头要往**右**摇', () {
      final f = compareAlignment(r(0.7, 0.3, 0.2, 0.4), r(0.2, 0.3, 0.2, 0.4));
      expect(f!.action, AlignAction.moveRight);
      expect(f.message, contains('向右移'));
    });

    test('目标在下方 → 相机要往**上**抬（抬镜头，画面里的东西才往下走）', () {
      final f = compareAlignment(r(0.3, 0.1, 0.3, 0.2), r(0.3, 0.7, 0.3, 0.2));
      expect(f!.action, AlignAction.moveUp);
      expect(f.dy, greaterThan(0));
    });

    test('目标在上方 → 相机要往**下**压', () {
      final f = compareAlignment(r(0.3, 0.7, 0.3, 0.2), r(0.3, 0.1, 0.3, 0.2));
      expect(f!.action, AlignAction.moveDown);
    });

    test('上下偏时提示必须是中文，不能漏出 AlignAction.xxx', () {
      // 之前这行用的是 `'$yAction'`（枚举插值），用户会看到
      // 「AlignAction.moveUp 30%」这种内部名字。
      final f = compareAlignment(r(0.3, 0.1, 0.3, 0.2), r(0.3, 0.7, 0.3, 0.2));
      expect(f!.message, isNot(contains('AlignAction')));
      expect(f.message, contains('相机往上抬'));
    });

    test('位置对了但主体太小 → 提示靠近', () {
      final f = compareAlignment(r(0.3, 0.3, 0.1, 0.1), r(0.3, 0.3, 0.4, 0.4));
      expect(f!.action, AlignAction.moveCloser);
      expect(f.sizeRatio, lessThan(1));
    });

    test('位置对了但主体太大 → 提示后退', () {
      final f = compareAlignment(r(0.2, 0.2, 0.6, 0.6), r(0.3, 0.3, 0.2, 0.2));
      expect(f!.action, AlignAction.moveBack);
      expect(f.sizeRatio, greaterThan(1));
    });

    test('位置偏 + 大小正常 → 先纠位置', () {
      // 主体大小跟目标差不多，但偏左（目标在右边）→ 相机要往左摇
      final f = compareAlignment(r(0.05, 0.3, 0.25, 0.35), r(0.6, 0.3, 0.25, 0.35));
      expect(f!.action, AlignAction.moveLeft);
      expect(f.degrees, isNotNull);
      expect(f.message, contains('约'));
    });

    test('主体严重偏小时，先让人靠近（位置等靠近完再说）', () {
      // 主体只占画面 1%，位置微偏
      final f = compareAlignment(r(0.40, 0.40, 0.10, 0.10), r(0.45, 0.45, 0.5, 0.5));
      expect(f!.action, AlignAction.moveCloser);
      // v0.9.3：人话（「走近一点」）—— 不用百分比
      expect(f.message, contains('走近'));
    });

    test('任一侧为空 → 返回 null（UI 显示兜底提示，不编数据）', () {
      expect(compareAlignment(null, r(0.3, 0.3, 0.2, 0.2)), isNull);
      expect(compareAlignment(r(0.3, 0.3, 0.2, 0.2), null), isNull);
      expect(compareAlignment(null, null), isNull);
    });

    test('容差可调：加大容差后同一情况算对齐', () {
      final strict = compareAlignment(
        r(0.30, 0.30, 0.25, 0.25), r(0.36, 0.30, 0.25, 0.25),
        thresholds: const AlignThresholds(posTolerance: 0.02, posFloor: 0.02),
      );
      final loose = compareAlignment(
        r(0.30, 0.30, 0.25, 0.25), r(0.36, 0.30, 0.25, 0.25),
        thresholds: const AlignThresholds(posTolerance: 0.10, posFloor: 0.02),
      );
      expect(strict!.aligned, isFalse);
      expect(loose!.aligned, isTrue);
    });

    test('绝对位移门槛：小偏移不喊「挪」（避免小主体被瞎指挥）', () {
      // 差 0.06：超过相对容差 0.05，但没超过绝对门槛 0.12
      final f = compareAlignment(
        r(0.30, 0.30, 0.25, 0.25), r(0.36, 0.30, 0.25, 0.25),
        thresholds: const AlignThresholds(posTolerance: 0.05),
      );
      expect(f!.aligned, isTrue, reason: '0.06 的偏移不该指挥用户动');
    });

    test('message 里有幅度百分比（用户能知道差多少）', () {
      final f = compareAlignment(r(0.1, 0.4, 0.2, 0.2), r(0.6, 0.4, 0.2, 0.2));
      expect(f!.message, contains('%'));
    });

    test('toJson 输出可序列化', () {
      final f = compareAlignment(r(0.1, 0.4, 0.2, 0.2), r(0.5, 0.4, 0.2, 0.2))!;
      expect(f.toJson()['action'], 'moveLeft');
      expect(f.toJson()['aligned'], false);
    });

    test('角度换算：往右偏 0.2 画面宽 → 约 13°', () {
      expect(panDegreesFor(0.2), closeTo(13.0, 0.1));
      expect(tiltDegreesFor(-0.2), closeTo(9.0, 0.1));
    });
  });
}
