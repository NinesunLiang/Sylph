import 'body_facts.dart';

/// 人体姿态扫描器的**接口** —— 留个缝：
/// 测试可以塞假实现，将来换引擎（MediaPipe 之类纯本地方案）也不用动上层。
abstract class BodyScanner {
  /// 扫一张照片里的人体，量出客观事实。扫不到就返回 null（**不编**）。
  Future<BodyFacts?> scanFile(String path);
}

/// v2 的默认实现：**什么都不量**，永远返回 null。
///
/// 为什么没有本地姿态模型：v1 用的 `google_mlkit_pose_detection` 带
/// `MlKitInitProvider`（ContentProvider 进程启动即执行），无谷歌服务的机型
/// （华为）启动即崩 —— v0.15.0–v0.19.1 全部中招。v2 在依赖层永久排除
/// 谷歌系包（tool/check_no_google.sh 每次构建机器验证），所以这里用空实现
/// 占位，而不是换另一个有风险的引擎。
///
/// 影响（诚实说明）：没有端上测量 → [BodyFacts] 永远为 null →
/// 分析请求里不带"量出来的人体数据"，模型只看图；界面上也不显示
/// "端上测量"卡片（数据不存在就不显示，不编）。
///
/// 将来若接纯本地姿态引擎（如 MediaPipe 的 Flutter 集成，无谷歌依赖），
/// 实现这个接口即可，上层（CoachPage / SuggestionAnalyzer）不用改。
class NoopBodyScanner implements BodyScanner {
  const NoopBodyScanner();

  @override
  Future<BodyFacts?> scanFile(String path) async => null;
}
