import 'dart:io';

import 'package:flutter/foundation.dart';

import 'features/analysis/face_light.dart';
import 'features/coach/model_config.dart';
import 'features/coach/suggestion.dart';
import 'features/poses/pose.dart';

/// 跨页共享的「当前拍摄方案」。
///
/// 为什么需要它：姿势页选好一个姿势后，要能「送到预览页」照着摆
/// （F3.7）。Flutter 里最省事又不用引第三方状态库的做法，
/// 就是这个 `ChangeNotifier` + `ValueListenableBuilder`/`AnimatedBuilder`。
///
/// 为什么不引 Provider/Riverpod：本项目的共享状态只有这一处，
/// 引一个状态管理库属于「实现 + 维护成本 > 增量增益」（哲学第 7 条）。
class AppSession extends ChangeNotifier {
  Pose? _activePose;

  /// 上一次「送到预览页」的请求序号。
  ///
  /// 为什么用计数而不是 bool：用户可能从姿势页连续送两次同一个姿势，
  /// bool 变化检测不出来（true → true 不触发）。计数每次都会变。
  int _sendSeq = 0;

  Suggestion? _activeSuggestion;

  /// v0.4.0：预览页跳系统相机拍完、回来检测到新照片后，
  /// 用户点「送教练」时暂存的照片文件。
  File? _pendingShot;

  /// 上一次「送教练点评」的请求序号（同样用计数防连点同一个文件）。
  int _shotSeq = 0;

  /// 用户在拍摄页选的**光线方向**（顺光/侧光/逆光，v0.9.0 环境指导）。
  FaceLightChoice? _lightDirection;

  /// 当前要照着摆的姿势（为空表示没有）。
  Pose? get activePose => _activePose;

  /// 用户声明的光线方向（没选 = null；教练点评时拼进 prompt）。
  FaceLightChoice? get lightDirection => _lightDirection;

  /// 记录一次光线方向选择（再点一次同方向 = 取消，传 null）。
  void setLightDirection(FaceLightChoice? choice) {
    _lightDirection = choice;
    notifyListeners();
  }

  /// 当前生效的构图建议（来自教练页，可为空）。
  Suggestion? get activeSuggestion => _activeSuggestion;

  /// 「送到预览页」的请求序号。UI 观察它来决定是否切到预览页。
  int get sendSeq => _sendSeq;

  /// v0.4.0：共享的模型配置存储（API Key 等）。
  ///
  /// 为什么挂在这里：教练页和设置页要在 IndexedStack 里**同时存活**，
  /// 设置页保存 Key 后教练页必须立刻看到（否则「设置里填 Key → AI 可用」
  /// 不成立）。挂 AppSession 上，两页拿同一实例，保存即双向生效。
  /// 生命周期 = App（main.dart 的根状态随 App 销毁时级联 dispose）。
  final ModelConfigStore modelConfig = ModelConfigStore();

  /// 待教练点评的照片（预览页送来的那张；空表示没有）。
  File? get pendingShot => _pendingShot;

  /// 「送教练点评」的请求序号。教练页观察它自动收图。
  int get shotSeq => _shotSeq;

  /// 是否处于「照着某个姿势拍」的模式。
  bool get hasActivePose => _activePose != null;

  /// 在姿势页点了「送到预览页」。
  void sendPoseToCamera(Pose pose) {
    _activePose = pose;
    _sendSeq++;
    notifyListeners();
  }

  /// 预览页用完了，清掉（避免下次进预览页还叠着老姿势）。
  void clearPose() {
    if (_activePose == null) return;
    _activePose = null;
    notifyListeners();
  }

  /// 预览页跳系统相机拍完，用户点「送教练」时调用。
  ///
  /// 教练页（IndexedStack 里常驻）监听 [shotSeq]，
  /// 看到序号变大就自己 [clearPendingShot] 取走。
  void sendShotToCoach(File file) {
    _pendingShot = file;
    _shotSeq++;
    notifyListeners();
  }

  /// 教练页收完图后调用，防止下次进页面又弹一次同一张。
  void clearPendingShot() {
    if (_pendingShot == null) return;
    _pendingShot = null;
    notifyListeners();
  }

  /// 教练页给出建议后设置目标（暂未接线，先留好接口）。
  void setSuggestion(Suggestion? suggestion) {
    _activeSuggestion = suggestion;
    notifyListeners();
  }

  @override
  void dispose() {
    modelConfig.dispose();
    super.dispose();
  }
}
