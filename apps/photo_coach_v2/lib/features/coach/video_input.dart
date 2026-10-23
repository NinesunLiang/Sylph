library;

import 'dart:async';
import 'dart:math' as math;
import 'dart:typed_data';

import 'suggestion.dart';

/// F2.12b —— 视频输入。
///
/// ## 策略：抽帧，不逐帧
/// 逐帧分析等于把视频拆成几百张图，token 和时间都爆炸（一张图 384 token，
/// 30 秒视频就是几万 token）。所以只抽 **最多 3 帧**：开头、中间、结尾。
///
/// ## 为什么抽这几帧
/// 用户拍视频通常是「在动」的：从 A 位置走到 B。头尾两帧能看出**走向**，
/// 中间帧防止「头尾差别大但其实只是抖了一下」的误判。
///
/// ## 可测性设计（重要）
/// 真解码要 `video_player`（原生），测试里跑不了。所以：
/// - [VideoFrameSource] 是接口，真实现用 video_player，测试用假的
/// - [mergeSuggestions] 是**纯函数**，多帧合并的全部逻辑都在这，可完整单测

/// 一帧画面。
class VideoFrame {
  const VideoFrame({
    required this.bytes,
    required this.index,
    required this.at,
    required this.totalDuration,
  });

  /// 编码后的图片字节（JPEG）。
  final Uint8List bytes;

  /// 第几帧（0 开始）。
  final int index;

  /// 这一帧在视频里的时间点。
  final Duration at;

  /// 视频总时长。
  final Duration totalDuration;

  /// 这一帧在时间轴上的位置（0–1），用于「走向」判断。
  double get position => totalDuration.inMilliseconds <= 0
      ? 0
      : (at.inMilliseconds / totalDuration.inMilliseconds).clamp(0.0, 1.0);

  bool get isFirst => index == 0;

  String get label => '第 ${index + 1} 帧 · ${at.inSeconds}s';
}

class VideoInputException implements Exception {
  VideoInputException(this.message);
  final String message;
  @override
  String toString() => 'VideoInputException: $message';
}

/// 抽帧来源。真实现在 `video_frame_source_impl.dart`（依赖 video_player），
/// 测试注入假的。
///
/// 注意它有**两个责任**：问时长 + 在指定时间点取原始像素。
/// 分成两个方法是因为真实现在取像素前必须先知道时长。
abstract class VideoFrameSource {
  /// 视频总时长。
  Future<Duration> duration(String videoPath);

  /// 在指定时间点取一帧原始像素。
  Future<RawFrame> frameAt(String videoPath, Duration at);
}

/// 一帧原始像素（还没编码成 JPEG）。
///
/// 为什么用 RGBA 而不是直接给 JPEG：原生解码器给的就是原始像素。
/// 编码成 JPEG 是上层 [VideoFrameExtractor] 的事 —— 那部分是纯函数，
/// 可以脱离原生单独测试。
class RawFrame {
  const RawFrame({
    required this.rgba,
    required this.width,
    required this.height,
    required this.at,
    required this.totalDuration,
  });

  /// 行优先 RGBA，长度 = width * height * 4。
  final Uint8List rgba;
  final int width;
  final int height;
  final Duration at;
  final Duration totalDuration;
}

/// 要抽哪几个时间点。
///
/// 抽成独立函数，方便单测边界（极短视频、零时长、超长视频）。
List<Duration> planFrameTimes(Duration total, {int maxFrames = 3}) {
  if (maxFrames <= 0) return const [];
  final ms = total.inMilliseconds;
  if (ms <= 0) return [Duration.zero];
  if (maxFrames == 1) return [Duration(milliseconds: ms ~/ 2)];

  // 均匀取样，但**避开最头和最尾**：
  // 开头常有黑帧/手抖，结尾常是放下手机的糊帧。
  // 取 5% ~ 95% 区间均匀分布。
  const startPct = 0.05;
  const endPct = 0.95;
  final out = <Duration>[];
  for (var i = 0; i < maxFrames; i++) {
    final t = maxFrames == 1 ? 0.5 : i / (maxFrames - 1);
    final pct = startPct + (endPct - startPct) * t;
    out.add(Duration(milliseconds: (ms * pct).round()));
  }
  return out;
}

/// 一帧的分析结果（成功或失败都记下来，不吞）。
class FrameAnalysis {
  const FrameAnalysis({
    required this.frame,
    this.suggestion,
    this.error,
    this.usedFallback = true,
  });

  final VideoFrame frame;
  final Suggestion? suggestion;
  final String? error;
  final bool usedFallback;

  bool get ok => suggestion != null && error == null;
}

/// 多帧合并的结果。
class MergedVideoAnalysis {
  const MergedVideoAnalysis({
    required this.suggestion,
    required this.frames,
    required this.notes,
    required this.successCount,
  });

  final Suggestion suggestion;
  final List<FrameAnalysis> frames;

  /// 合并过程中的说明（哪几帧失败、有没有矛盾）。
  final List<String> notes;

  final int successCount;

  bool get anySuccess => successCount > 0;
}

/// 把多帧建议合并成一条。
///
/// 规则（每条都有理由，且都有测试）：
/// 1. **位置/大小取最后一帧** —— 用户拍视频是在找位置，最后那一帧才是
///    他现在停在哪。取平均会把「已经站好了」也算成「还差一点」。
/// 2. **相机动作取中位数** —— 少数帧解析失败或被噪声带偏时，中位数比
///    平均值稳（平均值会被离群值拖走）。
/// 3. **曝光取中位数** —— 同上。
/// 4. **构图规则取出现次数最多的** —— 多数帧都认为是三分法，那就认它。
/// 5. **提示词（tips）去重后保留最后帧的** —— 避免把 3 帧的话堆成 9 条。
/// 6. **帧之间结论矛盾时明确说出来** —— 不能悄悄选一个。
MergedVideoAnalysis mergeSuggestions(List<FrameAnalysis> frames) {
  final notes = <String>[];
  final ok = frames.where((f) => f.suggestion != null).toList();

  if (ok.isEmpty) {
    final reason = frames.isEmpty
        ? '一帧都没抽出来'
        : '所有帧都分析失败（${frames.first.error ?? "未知原因"}）';
    return MergedVideoAnalysis(
      suggestion: Suggestion.fallback(reason: reason),
      frames: frames,
      notes: [
        reason,
        '已给出通用构图建议，但没有针对性分析',
      ],
      successCount: 0,
    );
  }

  final failed = frames.length - ok.length;
  if (failed > 0) {
    notes.add('${frames.length} 帧里有 $failed 帧没分析成功，已忽略');
  }

  final suggestions = [for (final f in ok) f.suggestion!];
  final last = suggestions.last;

  double median(List<double> xs) {
    if (xs.isEmpty) return 0;
    final s = [...xs]..sort();
    final mid = s.length ~/ 2;
    return s.length.isOdd ? s[mid] : (s[mid - 1] + s[mid]) / 2;
  }

  final pan = median([for (final s in suggestions) s.cameraMove.panDeg]);
  final tilt = median([for (final s in suggestions) s.cameraMove.tiltDeg]);
  final dolly = median([for (final s in suggestions) s.cameraMove.dollyM]);
  final zoom = median([for (final s in suggestions) s.cameraMove.zoom]);
  final ev = median([for (final s in suggestions) s.exposure.ev]);

  // 构图规则投票
  final votes = <String, int>{};
  for (final s in suggestions) {
    votes[s.composition.rule] = (votes[s.composition.rule] ?? 0) + 1;
  }
  final ranked = votes.entries.toList()
    ..sort((a, b) {
      final byCount = b.value.compareTo(a.value);
      return byCount != 0 ? byCount : a.key.compareTo(b.key);
    });
  final bestRule = ranked.first;
  if (ranked.length > 1) {
    notes.add('各帧判断的构图不一致（${ranked.map((e) => "${e.key}×${e.value}").join("、")}），'
        '按出现最多的「$bestRule.key」处理');
  }
  if (bestRule.value * 2 <= suggestions.length && suggestions.length > 1) {
    notes.add('注意：没有哪种构图占多数，建议自己再看一眼画面');
  }

  // 位置矛盾检测：头尾帧差异过大 → 说明用户在移动，不是静态构图
  if (suggestions.length >= 2) {
    final first = suggestions.first.subject.currentBox;
    final lastBox = last.subject.currentBox;
    if (first != null && lastBox != null) {
      final moved = (first.centerX - lastBox.centerX).abs() +
          (first.centerY - lastBox.centerY).abs();
      if (moved > 0.35) {
        notes.add('画面里主体位置变化很大，说明你在移动拍。'
            '下面按最后一帧的位置给建议');
      }
    }
  }

  // 曝光跨度大 → 光线在变（比如从暗处走到亮处）
  final evs = [for (final s in suggestions) s.exposure.ev];
  if (evs.length >= 2 && (evs.reduce(math.max) - evs.reduce(math.min)) > 1.0) {
    notes.add('各帧的曝光建议差很多，可能光线一直在变。建议先站定再测光');
  }

  final tips = <String>[];
  for (final t in last.tips) {
    if (!tips.contains(t)) tips.add(t);
  }

  // 拍摄方案（光照/人站哪/拍摄点/机位方向）取**最后一个非空**的：
  // 视频里用户在走动找位置，最后那帧才代表他现在的处境。
  ShootingPlan plan = const ShootingPlan();
  for (final s in suggestions.reversed) {
    if (!s.shootingPlan.isEmpty) {
      plan = s.shootingPlan;
      break;
    }
  }

  // 优缺点各帧去重合并（同一问题在不同帧重复出现，只留一条）
  final pros = <String>[];
  for (final s in suggestions) {
    for (final p in s.pros) {
      if (!pros.contains(p)) pros.add(p);
      if (pros.length >= 3) break;
    }
  }
  final critiques = <CritiqueItem>[];
  for (final s in suggestions) {
    for (final c in s.critiques) {
      if (critiques.any((x) => x.problem == c.problem)) continue;
      critiques.add(c);
      if (critiques.length >= 3) break;
    }
  }

  // 要素体检：按要素名跨帧合并，**同名的取更严重的那个**
  // （某一帧暴露出的问题，不该因为后面几帧没问题就被抹掉）
  final byName = <String, ElementCheck>{};
  for (final s in suggestions) {
    for (final e in s.elements) {
      final old = byName[e.name];
      if (old == null || e.verdict.severity > old.verdict.severity) {
        byName[e.name] = e;
      }
    }
  }
  final elements = byName.values.toList()
    ..sort((a, b) => b.verdict.severity - a.verdict.severity);

  final merged = Suggestion(
    schemaVersion: last.schemaVersion,
    composition: CompositionHint(
      rule: bestRule.key,
      // 置信度取最小：只要有一帧不确定，整体就不该显得很确定
      confidence: suggestions
          .map((s) => s.composition.confidence)
          .reduce(math.min),
      horizonTiltDeg: median([for (final s in suggestions) s.composition.horizonTiltDeg]),
    ),
    // 主体位置取最后一帧（用户在找位置，最后那帧才是现状）
    subject: last.subject,
    cameraMove: CameraMoveHint(
      panDeg: pan,
      tiltDeg: tilt,
      dollyM: dolly,
      zoom: zoom,
      hint: last.cameraMove.hint,
    ),
    exposure: ExposureHint(ev: ev, reason: last.exposure.reason),
    tips: tips,
    shootingPlan: plan,
    pros: pros,
    critiques: critiques,
    elements: elements,
    source: last.source,
  );

  notes.insert(0, '合并了 ${ok.length} 帧（相机动作/曝光取中位数，主体位置与拍摄方案取最后一帧）');

  return MergedVideoAnalysis(
    suggestion: merged,
    frames: frames,
    notes: notes,
    successCount: ok.length,
  );
}
