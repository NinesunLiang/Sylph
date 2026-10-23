import 'suggestion.dart';

/// 离线兜底建议。
///
/// ⚠️ 诚实声明：这里**没有图像识别**，给的是通用构图原则，不是「看到了你的图」。
/// 所以产出的 [Suggestion.source] 必须是 [SuggestionSource.ruleFallback]，
/// UI 上要明确标出来，不能让兜底冒充 AI 结论（零信任）。
///
/// 真正的离线主体定位：等一个**无谷歌依赖**的纯本地姿态引擎（如 MediaPipe）。
/// v1 用的那个插件带 ContentProvider，无谷歌服务机型启动即崩，v2 永不引回。
class OfflineTipEngine {
  const OfflineTipEngine();

  /// 把技术性的 reason 翻译成**给用户看的一句话**。
  ///
  /// 为什么需要：调用方传进来的 reason 是技术错误原文
  /// （`HTTP 500: server error` / `SocketException: ...` / `no_api_config`），
  /// 直接拼给用户看就是一堆英文异常。用户看到的是"App 出问题了"，
  /// 实际上只是"没接上模型，先用通用原则顶上"。
  ///
  /// 返回 null 表示**不用跟用户解释**（没原因是正常的，不是故障）。
  /// [reason] 是给人看的（中文优先），[detail] 是技术细节（如异常原文）。
  ///
  /// ⚠️ **分类必须同时看技术细节**：真机上出过这种情况 ——
  /// `reason` 是"AI 服务暂时不可用"，而真正的原因（TLS 握手失败）只在
  /// `detail` 里，于是给用户的提示**完全没法动手**（人类 2026-09-21 实机截图）。
  static String? userFacingReason(String reason, {String? detail}) {
    final r = reason.trim();
    final lower = '${detail ?? ''} $r'.toLowerCase();
    if (r.isEmpty && lower.trim().isEmpty) return null;

    // ---- 网络层：给**能动手**的话，不说废话 ----
    // TLS / 加密握手：真机上最常见的原因就是开了 VPN / 代理，或链路被拦
    if (lower.contains('handshake') ||
        lower.contains('certificate') ||
        lower.contains('tls') ||
        lower.contains('ssl')) {
      return '离线提示：连不上 AI（加密握手被打断）—— '
          '关掉 VPN / 代理，或换手机流量再试';
    }
    // DNS / 找不到服务器
    if (lower.contains('failed host') || lower.contains('host lookup')) {
      return '离线提示：连不上 AI（找不到服务器）—— 检查网络，或关掉代理再试';
    }
    // 连不上 / 断网
    if (lower.contains('socket') ||
        lower.contains('connection') ||
        lower.contains('network') ||
        lower.contains('network is unreachable')) {
      return '离线提示：现在连不上网，先用几条通用原则帮你';
    }
    // 超时
    if (lower.contains('timeout') || lower.contains('timed out')) {
      return '离线提示：模型响应超时，先用几条通用原则帮你';
    }
    // 没配模型
    if (lower.contains('no_api') || lower.contains('not_configured')) {
      return '离线提示：还没接上 AI 模型，先用几条通用原则帮你';
    }
    // HTTP 错误
    if (lower.startsWith('http') || lower.contains('status')) {
      return '离线提示：AI 服务暂时不可用，先用几条通用原则帮你';
    }
    // 模型回了看不懂的东西
    if (lower.contains('unparsable') || lower.contains('parse')) {
      return '离线提示：AI 返回的内容无法理解，先用几条通用原则帮你';
    }
    // 空响应
    if (lower.contains('empty') || lower.contains('no choices')) {
      return '离线提示：AI 这次没给出内容，先用几条通用原则帮你';
    }

    // 中文原因本来就是给人看的，原样带出
    final hasCjk = RegExp(r'[\u4e00-\u9fff]').hasMatch(r);
    if (hasCjk) return r;

    // 其它看不懂的英文/代号 → 不要端给用户
    return '离线提示：这次没能用上 AI，先用几条通用原则帮你';
  }

  /// [reason] 是**用户可读**的一句话（中文优先）；
  /// [detail] 是**技术细节**（如 `HTTP 500`、`SocketException`），
  /// 只进 [Suggestion.errorCode]，不进用户可见文案。
  Suggestion suggest({String reason = '', String? detail}) {
    final friendly = userFacingReason(reason, detail: detail);
    final tech = (detail ?? reason).trim();
    return Suggestion(
      composition: const CompositionHint(rule: 'rule_of_thirds'),
      subject: const SubjectHint(),
      cameraMove: const CameraMoveHint(
        hint: '把主体放在左或右三分之一线上，别放正中间',
      ),
      exposure: const ExposureHint(
        ev: 0,
        reason: '离线模式没有测光数据，出片时请在系统相机里手动调曝光补偿',
      ),
      tips: [
        // 必须告诉用户"这不是 AI 分析"，但要用中文说清楚
        if (friendly != null) friendly,
        '开相机网格线，把主体对到交叉点',
        '地平线放平，或压在上/下三分之一处',
        '头顶留一指宽空隙，脚下别切太多',
      ],
      source: SuggestionSource.ruleFallback,
      // 技术细节留在结构化字段里，给排查用，不进用户可见文案
      errorCode: tech.isEmpty ? null : tech,
    );
  }
}
