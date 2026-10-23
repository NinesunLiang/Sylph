import 'dart:async';

import 'package:flutter/foundation.dart';

import '../coach/suggestion.dart';
import 'alignment.dart';
import 'live_element_probe.dart';
import 'subject_detector.dart';

/// F2.11/F2.12 —— 实时虚拟引导的**循环**。
///
/// 数据流：
/// ```
/// 定时器（默认 150ms，v0.8.0 由 900ms 提速；抓帧重入锁仍是硬上限）
///   → 抓一帧（LiveFrameSource）
///   → 本地检测主体在哪（SubjectDetector，纯 Dart，无原生依赖）
///   → 跟目标框比 → 一句人话（compareAlignment）
///   → 通知 UI 重画（箭头 / 框 / 提示）
/// ```
///
/// 成本控制的取舍（写清楚，免得后人以为漏了）：
/// - **不用 `startImageStream`**：那个要写原生 MethodChannel 桥接
///   （CameraX/AVFoundation），代价大且本机没法验证。定时抓帧能达到
///   「每秒一次」的反馈节奏，对「挪两步再拍」这个场景够用。
/// - **抓完必须让出一拍**：抓帧期间不能重入（见 `_ticking`）。
/// - **不联网**：实时反馈绝不能走网络（往返 3–8 秒，用户挪一下就要重算）。
///
/// ⚠️ 当前限制（诚实标注）：这一版是**抓帧分析**，不是相机原生预览流。
/// 所以画面会有一次极短的中断感。要彻底顺滑需要 `startImageStream`，
/// 那是独立的原生工作量（FEATURES.md 里单列）。

/// 抓一帧画面。抽成接口是为了**可测** —— 真实现包相机，测试注入假的。
///
/// 之前直接依赖具体的 `CameraSession`，导致这个控制器完全测不了
/// （覆盖率只有 11%），4 个 bug 藏着没被发现。
abstract class LiveFrameSource {
  /// 相机可以抓帧了吗。
  bool get ready;

  /// 相机正忙（正在拍照）—— 这时不能插队。
  bool get busy;

  /// 抓一帧，返回图片字节。抓不到返回 null。
  Future<Uint8List?> grabFrame();
}

/// 连续失败多少次之后开始退避。
const int kBackoffAfterFailures = 2;

/// 退避时最多跳过几个周期。
const int kMaxBackoffSkips = 8;

class LiveGuideController extends ChangeNotifier {
  LiveGuideController({
    required this.source,
    SubjectDetector? detector,
    this.alignThresholds = AlignThresholds.standard,
    this.interval = const Duration(milliseconds: 150),
  }) : detector = detector ?? const SubjectDetector();

  /// 抓帧来源（公开：测试要能替换，UI 要能看状态）。
  final LiveFrameSource source;
  final SubjectDetector detector;
  final AlignThresholds alignThresholds;
  final Duration interval;

  /// 最近一次抓到并解析完的帧字节。
  ///
  /// v0.8.0：拍摄页的脸检测**搭车**这一帧（见 CameraPage._onLiveChanged），
  /// 不再自己重新抓帧——两次 takePicture 并发会撞 isTakingPicture。
  /// 测试可传 FakeFrameSource 验证「同帧复用」。
  Uint8List? lastFrame;

  Timer? _timer;
  bool _running = false;
  bool _ticking = false;
  bool _disposed = false;

  /// 第几代。每次 start/stop/pause 都 +1。
  ///
  /// 为什么要它：一次抓帧 + 解码可能耗时 1–2 秒，期间用户可能已经按了关闭。
  /// 没有这个代次，在途的结果回来后会**覆盖掉刚关掉的状态**
  /// （实测表现：关了实时引导，底下的提示还在跳）。
  int _generation = 0;

  /// 建议里的目标框（由 F2 的建议 JSON 提供）。
  Rect01? targetBox;

  /// 当前检测到的主体框。
  Rect01? currentBox;

  /// 最近一次对位反馈。
  AlignFeedback? feedback;

  /// 最近一帧里最该处理的**要素问题**（过曝/背景乱/主体贴边），没有就是 null。
  /// 完全由本地像素算出来，不联网。
  LiveIssue? issue;

  /// 最近一次检测的说明（没找到主体时是原因）。
  String status = '未开始';

  /// 累计跑了多少次。
  int ticks = 0;

  /// **连续**失败次数。成功一次就清零 —— 否则会一直涨，显示「一直失败」骗人。
  int consecutiveFailures = 0;

  /// 累计失败次数（给开发者看，不用于展示"当前状态"）。
  int totalFailures = 0;

  /// 还要跳过几个周期（每次 tick 减 1）。
  int _backoffSkips = 0;

  /// 当前退避**档位**。跟「剩余跳过数」分开，因为它才是稳定可读的状态：
  /// 剩余跳过数会被 tick 消费掉，随时读到 0，没法用来判断"是否在退避"。
  int _backoffLevel = 0;

  /// 当前退避档位（0 = 全速）。
  int get backoffLevel => _backoffLevel;

  /// 还要跳过几拍。
  int get backoffSkips => _backoffSkips;

  bool get running => _running;
  bool get hasSubject => currentBox != null;
  bool get aligned => feedback?.aligned ?? false;

  /// 是否正在退避（连续失败后降频）。
  bool get backingOff => _backoffLevel > 0;

  /// 给 UI 看的一句话统计。
  String get statsLabel {
    if (ticks == 0) return '还没分析过';
    if (consecutiveFailures > 0) {
      return '已分析 $ticks 帧 · 连续 $consecutiveFailures 次没测出来';
    }
    return '已分析 $ticks 帧 · 命中 ${ticks - totalFailures} 次';
  }

  void setTarget(Rect01? box) {
    targetBox = box;
    _recompute();
  }

  void start() {
    if (_running || _disposed) return;
    _running = true;
    _generation++;
    consecutiveFailures = 0;
    totalFailures = 0;
    _backoffSkips = 0;
    _backoffLevel = 0;
    status = '实时引导已开启';
    notifyListeners();
    _armTimer();
    unawaited(_tick());
  }

  void _armTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(interval, (_) => _tick());
  }

  /// 临时让出一拍（比如用户按了快门）。运行状态保持不变。
  void pause() {
    _generation++;
    _timer?.cancel();
    _timer = null;
  }

  void resume() {
    if (!_running || _disposed) return;
    _generation++;
    _armTimer();
  }

  void stop() {
    _generation++;
    _timer?.cancel();
    _timer = null;
    _backoffSkips = 0;
    _backoffLevel = 0;
    if (!_running) return;
    _running = false;
    currentBox = null;
    feedback = null;
    status = '实时引导已关闭';
    notifyListeners();
  }

  void toggle() => _running ? stop() : start();

  Future<void> _tick() async {
    if (!_running || _ticking || _disposed) return;

    // 退避：连续失败后先跳过几个周期，别疯了一样猛试（发热耗电）
    if (_backoffSkips > 0) {
      _backoffSkips--;
      return;
    }

    if (!source.ready || source.busy) return;

    final gen = _generation;
    _ticking = true;
    try {
      final bytes = await source.grabFrame();
      if (_disposed || gen != _generation) return;
      if (bytes == null) {
        _onFailure('这一帧没抓到画面');
        return;
      }
      // 留给搭车方（拍摄页脸检测/距离建议）复用，免二次抓帧。
      lastFrame = bytes;

      // 只解一次图：网格同时喂给「主体检测」和「要素探针」
      final grid = await detector.gridOf(bytes);
      if (_disposed || gen != _generation) return;
      final detection = detector.detectFromGrid(grid);
      if (_disposed || gen != _generation) return;

      ticks++;
      consecutiveFailures = 0;
      _backoffSkips = 0; // 好了就恢复正常节奏
      _backoffLevel = 0;
      currentBox = detection.found ? detection.box : null;
      // 本地要素探针：过曝 / 背景乱 / 主体贴边 —— 完全本地，不联网
      issue = probeTopIssue(grid, subjectBox: currentBox);
      status = detection.found
          ? detection.reason
          : '没找到主体：${detection.reason}';
      if (!detection.found) {
        // 「没找到主体」不算抓帧失败：相机是好的，只是画面里没主体。
        // 这种不该退避（用户可能正在挪，下一帧就找到了）。
        totalFailures++;
      }
      _recompute();
    } catch (e) {
      if (_disposed || gen != _generation) return;
      _onFailure('这一帧没测出来（$e）');
    } finally {
      _ticking = false;
    }
  }

  void _onFailure(String message) {
    issue = null; // 这一帧没测出来，旧的要素提示就是过期的，别留着
    totalFailures++;
    consecutiveFailures++;
    status = message;
    currentBox = null;
    feedback = null;

    if (consecutiveFailures >= kBackoffAfterFailures) {
      // ⚠️ 必须「每次失败多跳一档」。
      // 之前写成 `(_backoffSkips + 1).clamp(1, max)` 有个致命 bug：
      // _backoffSkips 每次 tick 会被减到 0，于是下次失败又变回 1 ——
      // 永远停在「只跳一格」，退避形同虚设（实测 400ms 还是抓了 21 次）。
      // 现在档位和剩余跳过数分开记录，档位只管涨。
      _backoffLevel = (_backoffLevel + 1).clamp(1, kMaxBackoffSkips);
      _backoffSkips = _backoffLevel;
    }
    if (!_disposed) notifyListeners();
  }

  void _recompute() {
    feedback = compareAlignment(currentBox, targetBox, thresholds: alignThresholds);
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    _timer?.cancel();
    _timer = null;
    super.dispose();
  }
}
