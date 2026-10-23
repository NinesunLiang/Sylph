import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:photo_coach_v2/features/coach/suggestion.dart' show Rect01;
import 'package:photo_coach_v2/features/guidance/live_guide_controller.dart';
import 'package:photo_coach_v2/features/guidance/live_element_probe.dart';
import 'package:photo_coach_v2/features/guidance/subject_detector.dart';

/// 实时引导控制器的测试。
///
/// 这个文件是**新加的**：之前这个控制器直接依赖具体的 CameraSession，
/// 完全没法测，覆盖率只有 11%，里面有 4 个 bug 一直没被发现。
/// 把抓帧抽成 [LiveFrameSource] 接口之后才测得起来。

/// 造一张「浅色背景 + 深色中间块」的 JPEG，让检测器能稳定找到主体。
Uint8List subjectJpeg({
  int w = 48,
  int h = 48,
  int boxX = 16,
  int boxY = 12,
  int boxW = 16,
  int boxH = 24,
}) {
  final image = img.Image(width: w, height: h);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final inBox = x >= boxX && x < boxX + boxW && y >= boxY && y < boxY + boxH;
      final v = inBox ? 20 : 230;
      image.setPixelRgb(x, y, v, v, v);
    }
  }
  return Uint8List.fromList(img.encodeJpg(image));
}

/// 假抓帧源：可控地返回画面 / null / 抛异常 / 延迟。
class FakeFrameSource implements LiveFrameSource {
  FakeFrameSource({
    this.ready = true,
    this.busy = false,
    this.bytes,
    this.error,
    this.delay = Duration.zero,
    this.nullEveryOther = false,
  });

  @override
  bool ready;
  @override
  bool busy;
  Uint8List? bytes;
  Object? error;
  Duration delay;
  bool nullEveryOther;

  int calls = 0;

  @override
  Future<Uint8List?> grabFrame() async {
    calls++;
    if (delay > Duration.zero) await Future<void>.delayed(delay);
    if (error != null) throw error!;
    if (nullEveryOther && calls.isOdd) return null;
    return bytes ?? subjectJpeg();
  }
}

void main() {
  const fast = Duration(milliseconds: 10);

  LiveGuideController make(LiveFrameSource src, {Duration? interval}) =>
      LiveGuideController(
        source: src,
        // 关掉 isolate：测试里更可控，也不会有跨 isolate 的类型问题
        detector: const SubjectDetector(useIsolate: false),
        interval: interval ?? fast,
      );

  group('LiveGuideController —— 生命周期', () {
    test('初始状态：没跑、没主体、统计为空', () {
      final c = make(FakeFrameSource());
      expect(c.running, isFalse);
      expect(c.hasSubject, isFalse);
      expect(c.ticks, 0);
      expect(c.statsLabel, '还没分析过');
      c.dispose();
    });

    test('start 之后 running=true，并且会立刻抓一帧（不等第一个周期）', () async {
      final src = FakeFrameSource();
      final c = make(src);
      c.start();
      expect(c.running, isTrue);
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(src.calls, greaterThanOrEqualTo(1));
      expect(c.ticks, greaterThanOrEqualTo(1));
      c.dispose();
    });

    test('每帧会跑本地要素探针：大片过曝 → 给出提示（完全本地，不联网）', () async {
      // 造一张"深灰底 + 一大片纯白"的图（模拟高光过曝）
      final im = img.Image(width: 64, height: 64);
      img.fill(im, color: img.ColorRgb8(60, 60, 60));
      img.fillRect(im,
          x1: 40, y1: 4, x2: 60, y2: 30, color: img.ColorRgb8(255, 255, 255));
      final src = FakeFrameSource(bytes: Uint8List.fromList(img.encodeJpg(im)));

      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 150));

      expect(c.issue, isNotNull, reason: '大片过曝必须被发现');
      expect(c.issue!.kind, LiveIssueKind.blownHighlight);
      expect(c.issue!.text, contains('减一点曝光'));
      c.dispose();
    });

    test('画面干净时不给要素提示（不许为了"有输出"而硬报）', () async {
      final flat = img.Image(width: 48, height: 48);
      img.fill(flat, color: img.ColorRgb8(128, 128, 128));
      final src = FakeFrameSource(bytes: Uint8List.fromList(img.encodeJpg(flat)));

      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 150));

      expect(c.issue, isNull);
      c.dispose();
    });

    test('重复 start 不会叠加定时器（抓帧次数不翻倍）', () async {
      final src = FakeFrameSource();
      final c = make(src, interval: const Duration(milliseconds: 50));
      c.start();
      c.start();
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 160));
      // 单个定时器 50ms 周期，160ms 内最多 4~5 次；叠加的话会翻好几倍
      expect(src.calls, lessThanOrEqualTo(6), reason: '实际 ${src.calls} 次 → 定时器叠了');
      c.dispose();
    });

    test('stop 之后不再抓帧，并清掉当前主体/反馈', () async {
      final src = FakeFrameSource();
      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 40));
      c.stop();

      expect(c.running, isFalse);
      expect(c.currentBox, isNull);
      expect(c.feedback, isNull);
      expect(c.status, contains('已关闭'));

      final after = src.calls;
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(src.calls, after, reason: 'stop 之后不该再抓帧');
      c.dispose();
    });

    test('toggle 来回切', () async {
      final c = make(FakeFrameSource());
      c.toggle();
      expect(c.running, isTrue);
      c.toggle();
      expect(c.running, isFalse);
      c.dispose();
    });

    test('pause 后不抓帧，resume 后恢复', () async {
      final src = FakeFrameSource();
      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 40));
      c.pause();
      final atPause = src.calls;
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(src.calls, atPause, reason: 'pause 期间不该抓帧');
      expect(c.running, isTrue, reason: 'pause 不改运行状态');

      c.resume();
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(src.calls, greaterThan(atPause));
      c.dispose();
    });

    test('ready=false 时不抓帧（相机没准备好）', () async {
      final src = FakeFrameSource(ready: false);
      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(src.calls, 0);
      c.dispose();
    });

    test('busy=true 时不抓帧（正在拍照，不插队）', () async {
      final src = FakeFrameSource(busy: true);
      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(src.calls, 0);
      c.dispose();
    });

    test('dispose 之后不再抓帧', () async {
      final src = FakeFrameSource();
      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 40));
      c.dispose();
      final after = src.calls;
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(src.calls, after);
    });
  });

  group('LiveGuideController —— 抓到主体', () {
    test('能检测出主体，并算出反馈', () async {
      final c = make(FakeFrameSource());
      c.setTarget(const Rect01(0.33, 0.25, 0.34, 0.5));
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 60));

      expect(c.hasSubject, isTrue);
      expect(c.currentBox, isNotNull);
      expect(c.feedback, isNotNull);
      expect(c.consecutiveFailures, 0);
      c.dispose();
    });

    test('没设目标框时也能检测，但 feedback 为 null（不编数据）', () async {
      final c = make(FakeFrameSource());
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(c.hasSubject, isTrue);
      expect(c.feedback, isNull);
      c.dispose();
    });

    test('检测不到主体时：不给假框，且不计入「抓帧失败」', () async {
      // 纯色图 → 检测器找不到主体
      final flat = img.Image(width: 32, height: 32);
      img.fill(flat, color: img.ColorRgb8(128, 128, 128));
      final src = FakeFrameSource(bytes: Uint8List.fromList(img.encodeJpg(flat)));
      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 60));

      expect(c.hasSubject, isFalse);
      expect(c.currentBox, isNull, reason: '不许瞎给框');
      expect(c.status, contains('没找到主体'));
      expect(c.consecutiveFailures, 0,
          reason: '「画面里没主体」不是抓帧失败，不该触发退避');
      c.dispose();
    });
  });

  group('LiveGuideController —— 失败与退避（新修的 bug）', () {
    test('grabFrame 返回 null → 记为失败', () async {
      final src = FakeFrameSource(nullEveryOther: true);
      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(c.totalFailures, greaterThanOrEqualTo(1));
      expect(c.status, isNotEmpty);
      c.dispose();
    });

    test('grabFrame 抛异常 → 不崩，记为失败', () async {
      final src = FakeFrameSource(error: StateError('相机挂了'));
      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(c.totalFailures, greaterThanOrEqualTo(1));
      expect(c.status, contains('没测出来'));
      expect(c.currentBox, isNull);
      c.dispose();
    });

    test('连续失败会退避：档位递增，且后期抓帧速率明显低于前期', () async {
      final src = FakeFrameSource(error: StateError('一直失败'));
      final c = make(src, interval: const Duration(milliseconds: 10));
      c.start();

      await Future<void>.delayed(const Duration(milliseconds: 100));
      final early = src.calls;
      expect(c.backoffLevel, greaterThan(1),
          reason: '失败几次后档位该涨上去，实际 ${c.backoffLevel}');

      await Future<void>.delayed(const Duration(milliseconds: 300));
      final late = src.calls - early;

      // 前 100ms 无退避（或退避轻），后 300ms 已退避到高挡
      // 只要「后 300ms 的平均速率」低于「前 100ms 的速率」就说明在退避
      final earlyRate = early / 100;
      final lateRate = late / 300;
      expect(lateRate, lessThan(earlyRate),
          reason: '前期 $early 次/100ms，后期 $late 次/300ms → 没退避');
      c.dispose();
    });

    test('抓帧一直失败也不会无限增长档位（有上限）', () async {
      final src = FakeFrameSource(error: StateError('一直失败'));
      final c = make(src, interval: const Duration(milliseconds: 5));
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 500));
      expect(c.backoffLevel, lessThanOrEqualTo(kMaxBackoffSkips));
      c.dispose();
    });

    test('成功一次就把「连续失败」清零（之前只增不减，显示"一直失败"骗人）', () async {
      var failMode = true;
      final src = _SwitchableSource(() => failMode);
      final c = make(src, interval: const Duration(milliseconds: 10));
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 120));
      expect(c.consecutiveFailures, greaterThan(0));

      failMode = false;
      await Future<void>.delayed(const Duration(milliseconds: 200));
      expect(c.consecutiveFailures, 0, reason: '成功之后必须清零');
      c.dispose();
    });

    test('statsLabel 反映真实情况', () async {
      final src = FakeFrameSource();
      final c = make(src);
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(c.statsLabel, contains('已分析'));
      expect(c.statsLabel, contains('命中'));
      c.dispose();
    });
  });

  group('LiveGuideController —— 在途结果不许污染已关闭的状态', () {
    test('抓帧很慢时按 stop，结果回来**不能**改状态', () async {
      final src = FakeFrameSource(delay: const Duration(milliseconds: 150));
      final c = make(src, interval: const Duration(seconds: 5));
      c.start();
      // 立刻停 —— 此时那一帧还在"路上"
      c.stop();

      await Future<void>.delayed(const Duration(milliseconds: 300));

      expect(c.running, isFalse);
      expect(c.currentBox, isNull, reason: '关了之后不许再有主体框');
      expect(c.feedback, isNull);
      expect(c.status, contains('已关闭'), reason: '状态不许被在途结果覆盖');
      c.dispose();
    });

    test('pause 期间回来的结果也不该生效', () async {
      final src = FakeFrameSource(delay: const Duration(milliseconds: 120));
      final c = make(src, interval: const Duration(seconds: 5));
      c.start();
      c.pause();
      await Future<void>.delayed(const Duration(milliseconds: 260));
      expect(c.currentBox, isNull);
      c.dispose();
    });

    test('反复 start/stop 不会让旧结果泄漏到新一轮', () async {
      final src = FakeFrameSource(delay: const Duration(milliseconds: 100));
      final c = make(src, interval: const Duration(seconds: 5));
      c.start();
      c.stop();
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 250));
      expect(c.running, isTrue);
      c.dispose();
    });
  });

  group('LiveGuideController —— 通知语义', () {
    test('stop 会通知监听者（UI 要重画）', () {
      final c = make(FakeFrameSource());
      var n = 0;
      c.addListener(() => n++);
      c.start();
      final afterStart = n;
      expect(afterStart, greaterThan(0));
      c.stop();
      expect(n, greaterThan(afterStart));
      c.dispose();
    });

    test('setTarget 触发重算', () {
      final c = make(FakeFrameSource());
      var n = 0;
      c.addListener(() => n++);
      c.setTarget(const Rect01(0.4, 0.4, 0.2, 0.2));
      expect(n, greaterThan(0));
      c.dispose();
    });
  });

  group('LiveGuideController —— lastFrame（v0.8.0 搭车帧）', () {
    test('抓到帧后 lastFrame 有值，初始为 null', () async {
      final c = make(FakeFrameSource());
      expect(c.lastFrame, isNull);
      c.start();
      // grabFrame 是 async 的：等首帧真正落盘。
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(c.lastFrame, isNotNull);
      c.stop();
      c.dispose();
    });

    test('grabFrame 返回 null 时 lastFrame 保持原值（不被清掉）', () async {
      final src = FakeFrameSource(nullEveryOther: true);
      final c = make(src, interval: const Duration(milliseconds: 5));
      c.start();
      await Future<void>.delayed(const Duration(milliseconds: 100));
      // 奇数次调用返回 null —— 只要中间成功过，lastFrame 就保留最近的成功帧。
      expect(c.lastFrame, isNotNull);
      c.stop();
      c.dispose();
    });

    test('v0.8.0 默认节奏 = 150ms（原 900ms，用户要求更快）', () {
      final c = LiveGuideController(
        source: FakeFrameSource(),
        detector: const SubjectDetector(useIsolate: false),
      );
      expect(c.interval, const Duration(milliseconds: 150));
      c.dispose();
    });

    test('150ms 节奏下确实在持续抓帧（不是一次性启动）', () async {
      final src = FakeFrameSource(delay: const Duration(milliseconds: 3));
      final c = LiveGuideController(
        source: src,
        detector: const SubjectDetector(useIsolate: false),
      );
      c.start();
      // 150ms 节奏 × 1.2s ≈ 8 次；首帧是立即抓的，容忍下界。
      await Future<void>.delayed(const Duration(milliseconds: 1200));
      expect(src.calls, greaterThan(4),
          reason: '150ms 节奏下 1.2s 内应抓到多次帧，实际 ${src.calls} 次');
      c.stop();
      c.dispose();
    });
  });
}

/// 可切换「一直失败 / 正常」的抓帧源。
class _SwitchableSource implements LiveFrameSource {
  _SwitchableSource(this.shouldFail);
  final bool Function() shouldFail;

  @override
  bool get ready => true;
  @override
  bool get busy => false;

  @override
  Future<Uint8List?> grabFrame() async {
    if (shouldFail()) throw StateError('故意失败');
    return subjectJpeg();
  }
}
