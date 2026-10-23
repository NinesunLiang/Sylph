import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:photo_coach_v2/features/coach/analyzer.dart';
import 'package:photo_coach_v2/features/coach/llm_client.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';
import 'package:photo_coach_v2/features/coach/video_frame_extractor.dart';
import 'package:photo_coach_v2/features/coach/video_input.dart';

/// 造一个假的抽帧来源 —— 测试里造不出真视频（要原生解码器）。
class FakeSource implements VideoFrameSource {
  FakeSource({
    this.total = const Duration(seconds: 10),
    this.failFrameAt,
    this.durationThrows = false,
    this.frameThrows = false,
    this.color = 120,
  });

  Duration total;
  Duration? failFrameAt;
  bool durationThrows;
  bool frameThrows;
  int color;

  final List<Duration> requested = [];

  @override
  Future<Duration> duration(String videoPath) async {
    if (durationThrows) throw StateError('读不到时长');
    return total;
  }

  @override
  Future<RawFrame> frameAt(String videoPath, Duration at) async {
    requested.add(at);
    if (frameThrows) throw StateError('解码失败');
    if (failFrameAt != null &&
        (at.inMilliseconds - failFrameAt!.inMilliseconds).abs() < 50) {
      throw StateError('这一帧解不出来');
    }
    return makeRawFrame(at: at, total: total, color: color);
  }
}

RawFrame makeRawFrame({
  required Duration at,
  required Duration total,
  int color = 120,
  int w = 32,
  int h = 24,
}) {
  final rgba = Uint8List(w * h * 4);
  for (var i = 0; i < w * h; i++) {
    rgba[i * 4] = color;
    rgba[i * 4 + 1] = color;
    rgba[i * 4 + 2] = color;
    rgba[i * 4 + 3] = 255;
  }
  return RawFrame(
    rgba: rgba,
    width: w,
    height: h,
    at: at,
    totalDuration: total,
  );
}

Suggestion sug({
  required Rect01? current,
  required Rect01? target,
  String rule = 'rule_of_thirds',
  double confidence = 0.8,
  double pan = 0,
  double tilt = 0,
  double ev = 0,
  List<String> tips = const [],
  ShootingPlan plan = const ShootingPlan(),
  List<String> pros = const [],
  List<CritiqueItem> critiques = const [],
  List<ElementCheck> elements = const [],
  SuggestionSource source = SuggestionSource.visionModel,
}) =>
    Suggestion(
      composition: CompositionHint(rule: rule, confidence: confidence),
      subject: SubjectHint(label: 'person', currentBox: current, targetBox: target),
      cameraMove: CameraMoveHint(panDeg: pan, tiltDeg: tilt, hint: 'hint'),
      exposure: ExposureHint(ev: ev),
      tips: tips,
      shootingPlan: plan,
      pros: pros,
      critiques: critiques,
      elements: elements,
      source: source,
    );

VideoFrame frame(int i, {int ms = 0}) => VideoFrame(
      bytes: Uint8List.fromList([1, 2, 3]),
      index: i,
      at: Duration(milliseconds: ms),
      totalDuration: const Duration(seconds: 10),
    );

void main() {
  group('planFrameTimes —— 抽哪几帧', () {
    test('默认 3 帧，都落在 5%–95% 区间内（避开开头结尾的黑帧/糊帧）', () {
      final t = planFrameTimes(const Duration(seconds: 10));
      expect(t.length, 3);
      expect(t.first.inMilliseconds, greaterThanOrEqualTo(500));
      expect(t.last.inMilliseconds, lessThanOrEqualTo(9500));
      // 单调递增
      expect(t[0] < t[1], isTrue);
      expect(t[1] < t[2], isTrue);
    });

    test('1 帧时取中间', () {
      final t = planFrameTimes(const Duration(seconds: 10), maxFrames: 1);
      expect(t.length, 1);
      expect(t.first.inMilliseconds, 5000);
    });

    test('maxFrames <= 0 返回空（别硬抽）', () {
      expect(planFrameTimes(const Duration(seconds: 5), maxFrames: 0), isEmpty);
      expect(planFrameTimes(const Duration(seconds: 5), maxFrames: -1), isEmpty);
    });

    test('零时长 → 只给 0 时刻（后面会被上层拦掉）', () {
      expect(planFrameTimes(Duration.zero), [Duration.zero]);
      expect(planFrameTimes(const Duration(milliseconds: -5)), [Duration.zero]);
    });

    test('超短视频也不越界', () {
      final t = planFrameTimes(const Duration(milliseconds: 100), maxFrames: 3);
      expect(t.length, 3);
      for (final d in t) {
        expect(d.inMilliseconds, inInclusiveRange(0, 100));
      }
    });

    test('要 5 帧就给 5 帧，均匀分布', () {
      final t = planFrameTimes(const Duration(seconds: 20), maxFrames: 5);
      expect(t.length, 5);
      final gaps = <int>[];
      for (var i = 1; i < t.length; i++) {
        gaps.add(t[i].inMilliseconds - t[i - 1].inMilliseconds);
      }
      expect(gaps.toSet().length, 1, reason: '间隔应该均匀');
    });
  });

  group('mergeSuggestions —— 多帧合并（F2.12b 的核心）', () {
    test('全部失败 → 兜底建议 + 说明，不假装有结论', () {
      final r = mergeSuggestions([
        FrameAnalysis(frame: frame(0), error: '网络挂了'),
        FrameAnalysis(frame: frame(1), error: '网络挂了'),
      ]);
      expect(r.anySuccess, isFalse);
      expect(r.successCount, 0);
      expect(r.suggestion.source, SuggestionSource.ruleFallback);
      expect(r.notes.first, contains('都分析失败'));
      expect(r.notes.any((n) => n.contains('没有针对性分析')), isTrue);
    });

    test('拍摄方案取**最后一个非空**的（视频里用户在找位置，最后那帧才算数）',
        () {
      final r = mergeSuggestions([
        FrameAnalysis(
          frame: frame(0),
          suggestion: sug(
            current: null,
            target: null,
            plan: const ShootingPlan(
              lighting: '逆光',
              position: '站到左边',
              subjectPosition: '人往左挪',
            ),
          ),
        ),
        FrameAnalysis(
          frame: frame(1),
          suggestion: sug(
            current: null,
            target: null,
            plan: const ShootingPlan(
              lighting: '光从左窗进来，侧光',
              position: '退后一步，手机降到胸口高度',
              direction: '左前方 45°，平视',
              subjectPosition: '人往窗边挪半步，脸朝窗',
            ),
          ),
        ),
      ]);

      expect(r.suggestion.shootingPlan.lighting, '光从左窗进来，侧光',
          reason: '应取最后一帧的方案');
      expect(r.suggestion.shootingPlan.subjectPosition, '人往窗边挪半步，脸朝窗');
      expect(r.suggestion.shootingPlan.isEmpty, isFalse);
    });

    test('优缺点跨帧去重合并，且**不编**（没有就空着）', () {
      final r = mergeSuggestions([
        FrameAnalysis(
          frame: frame(0),
          suggestion: sug(
            current: null,
            target: null,
            pros: const ['背景干净'],
            critiques: const [
              CritiqueItem(problem: '主体偏下', better: '手机上移一点'),
            ],
          ),
        ),
        FrameAnalysis(
          frame: frame(1),
          suggestion: sug(
            current: null,
            target: null,
            pros: const ['背景干净', '光线柔和'],
            critiques: const [
              CritiqueItem(problem: '主体偏下', better: '手机上移一点'),
              CritiqueItem(problem: '画面太满', better: '往后退半步'),
            ],
          ),
        ),
      ]);

      expect(r.suggestion.pros, ['背景干净', '光线柔和'],
          reason: '同一优点只留一条');
      expect(r.suggestion.critiques.length, 2, reason: '同一问题只留一条');
      expect(r.suggestion.critiques.map((c) => c.problem),
          containsAll(<String>['主体偏下', '画面太满']));
    });

    test('要素体检跨帧合并：同名取**更严重**的那个（问题不能被后面几帧抹掉）',
        () {
      final r = mergeSuggestions([
        FrameAnalysis(
          frame: frame(0),
          suggestion: sug(
            current: null,
            target: null,
            elements: const [
              ElementCheck(name: '眼神', verdict: ElementVerdict.problem, advice: '看向远处'),
              ElementCheck(name: '构图', verdict: ElementVerdict.good),
            ],
          ),
        ),
        FrameAnalysis(
          frame: frame(1),
          suggestion: sug(
            current: null,
            target: null,
            elements: const [
              // 这一帧眼神看着还行 —— 但不能因此抹掉上一帧发现的问题
              ElementCheck(name: '眼神', verdict: ElementVerdict.good),
              ElementCheck(name: '背景杂物', verdict: ElementVerdict.unclear),
            ],
          ),
        ),
      ]);

      final byName = {for (final e in r.suggestion.elements) e.name: e};
      expect(byName['眼神']!.verdict, ElementVerdict.problem,
          reason: '同名要素应取更严重的那个');
      expect(byName['眼神']!.advice, '看向远处');
      expect(byName.keys, containsAll(<String>['眼神', '构图', '背景杂物']));
      // 有问题的排最前
      expect(r.suggestion.elements.first.name, '眼神');
    });

    test('一帧都没抽到 → 也兜底，别崩', () {
      final r = mergeSuggestions([]);
      expect(r.anySuccess, isFalse);
      expect(r.notes.first, contains('一帧都没抽出来'));
    });

    test('部分失败 → 用成功的那些，并说明少了几帧', () {
      final r = mergeSuggestions([
        FrameAnalysis(
          frame: frame(0),
          suggestion: sug(current: const Rect01(0.1, 0.1, 0.2, 0.2),
              target: const Rect01(0.3, 0.3, 0.2, 0.2)),
        ),
        FrameAnalysis(frame: frame(1), error: '降级'),
        FrameAnalysis(
          frame: frame(2),
          suggestion: sug(current: const Rect01(0.3, 0.3, 0.2, 0.2),
              target: const Rect01(0.3, 0.3, 0.2, 0.2)),
        ),
      ]);
      expect(r.successCount, 2);
      expect(r.notes.any((n) => n.contains('2 帧没分析成功') || n.contains('1 帧没分析成功')), isTrue);
    });

    test('主体位置取最后一帧（用户拍视频是在找位置）', () {
      const first = Rect01(0.05, 0.05, 0.2, 0.2);
      const last = Rect01(0.35, 0.35, 0.3, 0.3);
      final r = mergeSuggestions([
        FrameAnalysis(frame: frame(0), suggestion: sug(current: first, target: last)),
        FrameAnalysis(frame: frame(1), suggestion: sug(current: last, target: last)),
      ]);
      expect(r.suggestion.subject.currentBox!.left, closeTo(0.35, 1e-9));
      expect(r.suggestion.subject.currentBox!.width, closeTo(0.3, 1e-9));
    });

    test('相机动作取中位数（离群帧带不偏）', () {
      final r = mergeSuggestions([
        FrameAnalysis(frame: frame(0), suggestion: sug(current: null, target: null, pan: -10)),
        FrameAnalysis(frame: frame(1), suggestion: sug(current: null, target: null, pan: -8)),
        FrameAnalysis(frame: frame(2), suggestion: sug(current: null, target: null, pan: 40)), // 离群
      ]);
      expect(r.suggestion.cameraMove.panDeg, closeTo(-8, 1e-9),
          reason: '平均值会是 7.3，中位数才是 -8');
    });

    test('偶数帧时中位数取中间两个的平均', () {
      final r = mergeSuggestions([
        FrameAnalysis(frame: frame(0), suggestion: sug(current: null, target: null, ev: -1)),
        FrameAnalysis(frame: frame(1), suggestion: sug(current: null, target: null, ev: 1)),
      ]);
      expect(r.suggestion.exposure.ev, closeTo(0, 1e-9));
    });

    test('构图规则按出现次数投票，落选要说出来', () {
      final r = mergeSuggestions([
        FrameAnalysis(frame: frame(0), suggestion: sug(current: null, target: null, rule: 'centered')),
        FrameAnalysis(frame: frame(1), suggestion: sug(current: null, target: null, rule: 'rule_of_thirds')),
        FrameAnalysis(frame: frame(2), suggestion: sug(current: null, target: null, rule: 'rule_of_thirds')),
      ]);
      expect(r.suggestion.composition.rule, 'rule_of_thirds');
      expect(r.notes.any((n) => n.contains('不一致')), isTrue);
    });

    test('票数打平时按字母序稳定选一个（结果可复现）', () {
      final r = mergeSuggestions([
        FrameAnalysis(frame: frame(0), suggestion: sug(current: null, target: null, rule: 'symmetry')),
        FrameAnalysis(frame: frame(1), suggestion: sug(current: null, target: null, rule: 'centered')),
      ]);
      expect(r.suggestion.composition.rule, 'centered');
      expect(r.notes.any((n) => n.contains('没有哪种构图占多数')), isTrue);
    });

    test('置信度取最小值（有一帧不确定，整体就不该显得笃定）', () {
      final r = mergeSuggestions([
        FrameAnalysis(frame: frame(0), suggestion: sug(current: null, target: null, confidence: 0.95)),
        FrameAnalysis(frame: frame(1), suggestion: sug(current: null, target: null, confidence: 0.30)),
      ]);
      expect(r.suggestion.composition.confidence, closeTo(0.30, 1e-9));
    });

    test('tips 取最后一帧并去重', () {
      final r = mergeSuggestions([
        FrameAnalysis(frame: frame(0), suggestion: sug(current: null, target: null, tips: ['A', 'B'])),
        FrameAnalysis(frame: frame(1), suggestion: sug(current: null, target: null, tips: ['B', 'C', 'B'])),
      ]);
      expect(r.suggestion.tips, ['B', 'C']);
    });

    test('主体位移大 → 提示「你在移动拍」', () {
      final r = mergeSuggestions([
        FrameAnalysis(
          frame: frame(0),
          suggestion: sug(current: const Rect01(0.05, 0.05, 0.2, 0.2), target: null),
        ),
        FrameAnalysis(
          frame: frame(1),
          suggestion: sug(current: const Rect01(0.6, 0.6, 0.2, 0.2), target: null),
        ),
      ]);
      expect(r.notes.any((n) => n.contains('移动')), isTrue);
    });

    test('曝光建议跨度大 → 提示光线在变', () {
      final r = mergeSuggestions([
        FrameAnalysis(frame: frame(0), suggestion: sug(current: null, target: null, ev: -1.5)),
        FrameAnalysis(frame: frame(1), suggestion: sug(current: null, target: null, ev: 1.5)),
      ]);
      expect(r.notes.any((n) => n.contains('光线')), isTrue);
    });

    test('合并结果的第一条说明写清用了什么规则（可追溯）', () {
      final r = mergeSuggestions([
        FrameAnalysis(frame: frame(0), suggestion: sug(current: null, target: null)),
      ]);
      expect(r.notes.first, contains('合并了 1 帧'));
      expect(r.notes.first, contains('中位数'));
      expect(r.notes.first, contains('最后一帧'));
    });

    test('来源跟着最后一帧（不冒充 AI）', () {
      final r = mergeSuggestions([
        FrameAnalysis(
          frame: frame(0),
          suggestion: sug(current: null, target: null, source: SuggestionSource.visionModel),
        ),
        FrameAnalysis(
          frame: frame(1),
          suggestion: sug(current: null, target: null, source: SuggestionSource.ruleFallback),
        ),
      ]);
      expect(r.suggestion.source, SuggestionSource.ruleFallback);
    });
  });

  group('encodeRgbaToJpeg —— 原始像素 → JPEG（纯函数）', () {
    test('尺寸非法返回 null（不抛）', () {
      expect(encodeRgbaToJpeg(Uint8List(0), 0, 0), isNull);
      expect(encodeRgbaToJpeg(Uint8List(16), -1, 4), isNull);
    });

    test('缓冲区比声明的小 → null（防越界读）', () {
      expect(encodeRgbaToJpeg(Uint8List(10), 4, 4), isNull);
    });

    test('正常输入产出可解码的 JPEG，颜色对得上', () {
      final raw = makeRawFrame(
        at: Duration.zero,
        total: const Duration(seconds: 1),
        color: 200,
        w: 16,
        h: 16,
      );
      final jpg = encodeRgbaToJpeg(raw.rgba, 16, 16)!;
      final decoded = img.decodeImage(jpg)!;
      expect(decoded.width, 16);
      final p = decoded.getPixel(8, 8);
      expect(p.r, closeTo(200, 6));
    });

    test('超长边会被缩到 maxSide 以内，长宽比保持', () {
      final raw = makeRawFrame(
        at: Duration.zero,
        total: const Duration(seconds: 1),
        w: 400,
        h: 200,
      );
      final jpg = encodeRgbaToJpeg(raw.rgba, 400, 200, maxSide: 100)!;
      final decoded = img.decodeImage(jpg)!;
      expect(decoded.width, 100);
      expect(decoded.height, 50);
    });

    test('本来就小就不放大', () {
      final raw = makeRawFrame(
        at: Duration.zero,
        total: const Duration(seconds: 1),
        w: 20,
        h: 10,
      );
      final decoded = img.decodeImage(
        encodeRgbaToJpeg(raw.rgba, 20, 10, maxSide: 1024)!,
      )!;
      expect(decoded.width, 20);
      expect(decoded.height, 10);
    });
  });

  group('VideoFrameExtractor —— 抽帧编排', () {
    test('正常抽 3 帧，时间点是规划出来的那些', () async {
      final src = FakeSource(total: const Duration(seconds: 10));
      final ex = VideoFrameExtractor(source: src, maxSide: 64);
      final frames = await ex.extract('/tmp/fake.mp4');

      expect(frames.length, 3);
      expect(src.requested.length, 3);
      expect(frames.first.index, 0);
      expect(frames.first.totalDuration, const Duration(seconds: 10));
      expect(frames.first.bytes, isNotEmpty);
      // 每帧都能解码
      for (final f in frames) {
        expect(img.decodeImage(f.bytes), isNotNull);
      }
    });

    test('空路径直接拒绝', () async {
      final ex = VideoFrameExtractor(source: FakeSource());
      expect(
        () => ex.extract('   '),
        throwsA(isA<VideoInputException>()),
      );
    });

    test('读不到时长 → 明确报错，不硬跑', () async {
      final ex = VideoFrameExtractor(source: FakeSource(durationThrows: true));
      await expectLater(
        ex.extract('/tmp/x.mp4'),
        throwsA(predicate((e) =>
            e is VideoInputException && e.message.contains('读不到视频时长'))),
      );
    });

    test('零时长视频 → 拒绝并说明', () async {
      final ex = VideoFrameExtractor(
        source: FakeSource(total: Duration.zero),
      );
      await expectLater(
        ex.extract('/tmp/x.mp4'),
        throwsA(predicate(
            (e) => e is VideoInputException && e.message.contains('时长是 0'))),
      );
    });

    test('单帧解码失败 → 跳过那一帧，其余照用', () async {
      // 3 帧的时间点约在 500 / 5000 / 9500ms
      final src = FakeSource(
        total: const Duration(seconds: 10),
        failFrameAt: const Duration(milliseconds: 5000),
      );
      final frames =
          await VideoFrameExtractor(source: src, maxSide: 64).extract('/tmp/x.mp4');
      expect(frames.length, 2);
      expect(src.requested.length, 3, reason: '还是应该试过 3 个时间点');
      expect(frames[1].index, 1, reason: 'index 要重新编号，不能有洞');
    });

    test('全部帧都失败 → 报错说明试了哪几个时间点', () async {
      final ex = VideoFrameExtractor(source: FakeSource(frameThrows: true));
      await expectLater(
        ex.extract('/tmp/x.mp4'),
        throwsA(predicate((e) =>
            e is VideoInputException && e.message.contains('没抽到画面'))),
      );
    });

    test('抽出来的帧是缩放过的（省 token）', () async {
      final src = FakeSource(total: const Duration(seconds: 4));
      final frames = await VideoFrameExtractor(source: src, maxSide: 10)
          .extract('/tmp/x.mp4');
      final decoded = img.decodeImage(frames.first.bytes)!;
      expect(decoded.width, lessThanOrEqualTo(10));
    });

    test('VideoFrame.label 有帧号和时间（UI 要显示）', () {
      expect(frame(0, ms: 1500).label, contains('第 1 帧'));
      expect(frame(0, ms: 1500).label, contains('1s'));
      expect(frame(0).isFirst, isTrue);
      expect(frame(1).isFirst, isFalse);
    });

    test('VideoFrame.position 是归一化时间（0–1）', () {
      final f = VideoFrame(
        bytes: Uint8List(1),
        index: 1,
        at: const Duration(seconds: 5),
        totalDuration: const Duration(seconds: 10),
      );
      expect(f.position, closeTo(0.5, 1e-9));
    });

    test('总时长为 0 时 position 不炸（防除零）', () {
      final f = VideoFrame(
        bytes: Uint8List(1),
        index: 0,
        at: Duration.zero,
        totalDuration: Duration.zero,
      );
      expect(f.position, 0);
    });
  });

  _endToEndTests();
}

// ---------------------------------------------------------------------------
// 端到端：抽帧 → 逐帧调模型（脚本化客户端，不联网）→ 合并
// 这是「视频链路」能验证到的最深处：不联网、不需要原生解码器，
// 但把抽帧、逐帧分析、降级、合并全部分支都跑了一遍。
// ---------------------------------------------------------------------------

String _sugBody({
  required String box,
  String rule = 'rule_of_thirds',
  double confidence = 0.9,
  double pan = -5,
  double ev = -0.3,
  String hint = '左一点',
  String tips = '["放三分之一线"]',
}) =>
    '{"schema_version":"1.0",'
    '"composition":{"rule":"$rule","confidence":$confidence,"horizon_tilt_deg":0},'
    '"subject":{"label":"person","current_box":$box,"target_box":[0.33,0.25,0.2,0.5]},'
    '"camera_move":{"pan_deg":$pan,"tilt_deg":2,"dolly_m":0,"zoom":1.0,"hint":"$hint"},'
    '"exposure":{"ev":$ev,"reason":"高光"},'
    '"tips":$tips}';

/// 按顺序返回预设响应；用完就报 500（模拟模型/网络挂掉）。
class _ScriptedClient extends VisionLlmClient {
  _ScriptedClient(this.bodies)
      : super(
          config: const ApiConfig(
            endpoint: 'https://fake.local/chat/completions',
            apiKey: 'sk-fake',
            mode: ProxyMode.direct,
          ),
        );

  final List<String> bodies;
  int calls = 0;

  @override
  Future<LlmRawResult> analyzeImage({
    required String dataUrl,
    required String prompt,
    String mimeType = 'image/jpeg',
  }) async {
    calls++;
    if (calls > bodies.length) {
      throw LlmException('HTTP 500: scripted failure', statusCode: 500);
    }
    final text = bodies[calls - 1];
    return LlmRawResult(text: text, decodedJson: extractJson(text));
  }

  @override
  void close() {}
}

Future<List<VideoFrame>> _frames({
  Duration total = const Duration(seconds: 10),
  Duration? failFrameAt,
}) =>
    VideoFrameExtractor(
      source: FakeSource(total: total, failFrameAt: failFrameAt),
      maxSide: 64,
    ).extract('/tmp/fake.mp4');

void _endToEndTests() {
  const cfg = ApiConfig(
    endpoint: 'https://fake.local/chat/completions',
    apiKey: 'sk-fake',
    mode: ProxyMode.direct,
  );

  group('视频端到端：抽帧 → 模型 → 合并（不联网）', () {
    test('3 帧全部成功 → 主体位置取最后一帧，相机动作取中位数', () async {
      final frames = await _frames();
      expect(frames.length, 3);

      final client = _ScriptedClient([
        _sugBody(box: '[0.05,0.05,0.2,0.2]', pan: -20),
        _sugBody(box: '[0.20,0.20,0.2,0.2]', pan: -5),
        _sugBody(box: '[0.40,0.40,0.2,0.2]', pan: -6),
      ]);
      final analyzer = SuggestionAnalyzer(config: cfg, client: client);

      final merged = await analyzer.analyzeFrames(frames);

      expect(merged.successCount, 3);
      expect(merged.anySuccess, isTrue);
      // 位置取最后一帧
      expect(merged.suggestion.subject.currentBox!.left, closeTo(0.40, 1e-9));
      // 中位数是 -6，不是平均 -10.33
      expect(merged.suggestion.cameraMove.panDeg, closeTo(-6, 1e-9));
      expect(merged.notes.first, contains('合并了 3 帧'));
      expect(client.calls, 3, reason: '每帧都该调一次模型');

      analyzer.dispose();
    });

    test('模型全挂 → 合并走兜底，并说明没有针对性分析', () async {
      final frames = await _frames(total: const Duration(seconds: 8));
      final client = _ScriptedClient(const []);
      final analyzer = SuggestionAnalyzer(config: cfg, client: client);

      final merged = await analyzer.analyzeFrames(frames);

      expect(merged.anySuccess, isFalse);
      expect(merged.successCount, 0);
      expect(merged.suggestion.source, SuggestionSource.ruleFallback);
      expect(merged.notes.any((n) => n.contains('没有针对性分析')), isTrue);
      analyzer.dispose();
    });

    test('抽帧阶段少了一帧（中间那帧解不出来）→ 只说一次，不重复报', () async {
      final frames = await _frames(failFrameAt: const Duration(milliseconds: 5000));
      expect(frames.length, 2, reason: '抽帧层已经把失败的帧跳过了');

      final client = _ScriptedClient([
        _sugBody(box: '[0.1,0.1,0.2,0.2]'),
        _sugBody(box: '[0.3,0.3,0.2,0.2]'),
      ]);
      final analyzer = SuggestionAnalyzer(config: cfg, client: client);
      final merged = await analyzer.analyzeFrames(frames);

      expect(merged.successCount, 2);
      // 抽帧层丢掉的帧不会出现在 frames 里 —— 不会重复报同一件事
      expect(merged.frames.length, 2);
      expect(merged.notes.first, contains('合并了 2 帧'));
      analyzer.dispose();
    });

    test('模型回了废话（抠不出 JSON）→ 那一帧算失败，其余照用', () async {
      final frames = await _frames();
      final client = _ScriptedClient([
        _sugBody(box: '[0.1,0.1,0.2,0.2]'),
        '抱歉，这个视频我看不太清楚。',
        _sugBody(box: '[0.4,0.4,0.2,0.2]'),
      ]);
      final analyzer = SuggestionAnalyzer(config: cfg, client: client);
      final merged = await analyzer.analyzeFrames(frames);

      expect(merged.successCount, 2);
      expect(merged.frames.length, 3);
      expect(merged.frames.where((f) => !f.ok).length, 1);
      expect(merged.notes.any((n) => n.contains('没分析成功')), isTrue);
      // 失败的那帧标注原因，不静默
      final bad = merged.frames.firstWhere((f) => !f.ok);
      expect(bad.error, isNotNull);
      analyzer.dispose();
    });

    test('各帧构图不一致 → 投票决定并说明（可追溯）', () async {
      final frames = await _frames();
      final client = _ScriptedClient([
        _sugBody(box: '[0.1,0.1,0.2,0.2]', rule: 'centered'),
        _sugBody(box: '[0.2,0.2,0.2,0.2]', rule: 'symmetry'),
        _sugBody(box: '[0.3,0.3,0.2,0.2]', rule: 'symmetry'),
      ]);
      final analyzer = SuggestionAnalyzer(config: cfg, client: client);
      final merged = await analyzer.analyzeFrames(frames);

      expect(merged.suggestion.composition.rule, 'symmetry');
      expect(merged.notes.any((n) => n.contains('不一致')), isTrue);
      analyzer.dispose();
    });

    test('零帧输入 → 兜底，不崩', () async {
      final analyzer = SuggestionAnalyzer(
        config: cfg,
        client: _ScriptedClient(const []),
      );
      final merged = await analyzer.analyzeFrames(const []);
      expect(merged.anySuccess, isFalse);
      expect(merged.notes.first, contains('一帧都没抽出来'));
      analyzer.dispose();
    });
  });
}
