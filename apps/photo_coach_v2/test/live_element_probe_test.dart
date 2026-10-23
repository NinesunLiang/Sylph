import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart' show Rect01;
import 'package:photo_coach_v2/features/guidance/live_element_probe.dart';
import 'package:photo_coach_v2/features/guidance/subject_detector.dart' show RgbGrid;

/// 实时要素探针的测试。
///
/// 这一层的价值在于：**完全本地、不联网、不花钱，而且能离线验**——
/// 不需要真机、不需要模型。所以这里断言要尽量具体。
///
/// 同时守诚实：判不出"那是什么东西"，就绝不在文案里编出来。
void main() {
  /// 造一张纯色图。
  RgbGrid solid(int w, int h, double v) {
    final n = w * h;
    return RgbGrid(
      Float32List(n)..fillRange(0, n, v),
      Float32List(n)..fillRange(0, n, v),
      Float32List(n)..fillRange(0, n, v),
      w,
      h,
    );
  }

  /// 在纯色底上把一块区域刷成另一个值。
  void paint(RgbGrid g, int x0, int y0, int w, int h, double v) {
    for (var y = y0; y < y0 + h && y < g.height; y++) {
      for (var x = x0; x < x0 + w && x < g.width; x++) {
        final i = y * g.width + x;
        g.r[i] = v;
        g.g[i] = v;
        g.b[i] = v;
      }
    }
  }

  /// 在区域内画棋盘格（高边缘密度 = "乱"）。
  void checker(RgbGrid g, int x0, int y0, int w, int h) {
    for (var y = y0; y < y0 + h && y < g.height; y++) {
      for (var x = x0; x < x0 + w && x < g.width; x++) {
        final v = ((x + y) % 2 == 0) ? 0.85 : 0.15;
        final i = y * g.width + x;
        g.r[i] = v;
        g.g[i] = v;
        g.b[i] = v;
      }
    }
  }

  group('过曝', () {
    test('三通道全顶到 1 的像素够多 → 报过曝，且给出真实位置', () {
      final g = solid(60, 60, 0.4);
      paint(g, 40, 5, 15, 15, 1.0); // 右上角一片白

      final issue = probeTopIssue(g);
      expect(issue, isNotNull);
      expect(issue!.kind, LiveIssueKind.blownHighlight);
      expect(issue.text, contains('过曝'));
      expect(issue.text, contains('减一点曝光'));
      // 位置必须真的对得上：x 大约从 40/60 开始
      expect(issue.rect, isNotNull);
      expect(issue.rect!.left, closeTo(40 / 60, 0.02));
      expect(issue.rect!.top, closeTo(5 / 60, 0.02));
    });

    test('只有零星几个亮像素 → 不报（免得全是噪声提示）', () {
      final g = solid(60, 60, 0.4);
      paint(g, 10, 10, 2, 2, 1.0); // 4/3600 ≈ 0.1%
      expect(probeTopIssue(g), isNull);
    });

    test('只是"比较亮"（0.9）不算过曝 —— 还没白到没细节', () {
      final g = solid(60, 60, 0.9);
      expect(probeTopIssue(g), isNull);
    });
  });

  group('背景杂乱', () {
    test('背景有一块明显更花 → 报背景乱，位置指向那一块', () {
      final g = solid(60, 60, 0.5); // 均匀干净的背景
      checker(g, 42, 0, 18, 20); // 右上角一块棋盘（很"花"）
      // 主体在左下角，离那块远
      const subject = Rect01(0.05, 0.6, 0.3, 0.35);

      final issue = probeTopIssue(g, subjectBox: subject);
      expect(issue, isNotNull);
      expect(issue!.kind, LiveIssueKind.busyBackground);
      expect(issue.text, contains('背景'));
      expect(issue.text, contains('乱'));
      // 必须指向右上那块（第 3 列）
      expect(issue.rect, isNotNull);
      expect(issue.rect!.left, greaterThan(0.6));
    });

    test('整张都干净 → 不报', () {
      final g = solid(60, 60, 0.5);
      expect(probeTopIssue(g, subjectBox: const Rect01(0.1, 0.1, 0.3, 0.3)),
          isNull);
    });

    test('判不出"那是什么东西" → 文案里不许出现具体物体名', () {
      final g = solid(60, 60, 0.5);
      checker(g, 42, 0, 18, 20);
      final issue = probeTopIssue(g, subjectBox: const Rect01(0.05, 0.6, 0.3, 0.35));

      for (final word in ['垃圾桶', '路人', '电线杆', '车']) {
        expect(issue!.text, isNot(contains(word)),
            reason: '本地只能算出"乱"，编出物体名就是骗人');
      }
    });
  });

  group('主体贴边', () {
    test('主体框贴到左边缘 → 提示往中间放', () {
      final g = solid(60, 60, 0.5);
      final issue = probeTopIssue(g, subjectBox: const Rect01(0.0, 0.3, 0.2, 0.4));
      expect(issue, isNotNull);
      expect(issue!.kind, LiveIssueKind.subjectClipped);
      expect(issue.text, contains('左'));
      expect(issue.text, contains('中间'));
    });

    test('主体在画面中间 → 不报贴边', () {
      final g = solid(60, 60, 0.5);
      expect(probeTopIssue(g, subjectBox: const Rect01(0.35, 0.3, 0.2, 0.4)),
          isNull);
    });
  });

  group('优先级', () {
    test('过曝比贴边更严重 → 先报过曝', () {
      final g = solid(60, 60, 0.4);
      paint(g, 20, 20, 20, 20, 1.0); // 大片过曝
      final issue =
          probeTopIssue(g, subjectBox: const Rect01(0.0, 0.0, 0.3, 0.9));
      expect(issue!.kind, LiveIssueKind.blownHighlight);
    });
  });

  group('边界', () {
    test('空网格 / 极小网格不崩', () {
      expect(probeTopIssue(solid(1, 1, 0.5)), isNull);
      expect(probeTopIssue(solid(2, 2, 0.5)), isNull);
    });

    test('没有主体框也能跑（只是不报贴边）', () {
      final g = solid(60, 60, 0.5);
      expect(probeTopIssue(g), isNull);
    });
  });
}
