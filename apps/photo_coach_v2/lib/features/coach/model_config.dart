import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'llm_client.dart';

/// 共享的模型配置存储（v0.4.0：设置页开放第二个入口后提出）。
///
/// 为什么独立成类：
/// v0.3.0 之前，API Key 的读取/保存逻辑 + 三个输入框全在 CoachPage 的
/// State 私有代码里（_loadApiConfig/_saveApiConfig/_ApiConfigCard），
/// 设置页拿不到这个入口 —— 用户真机反馈「ai功能没有输入apikey的能力，
/// 我需要设置里面有设置apikey」。抽成可共享的 [ChangeNotifier] 后，
/// 教练页和设置页用**同一个配置源**：任一页保存，另一页立即可见
/// （两页在 IndexedStack 里保持存活，不依赖重建）。
///
/// 存储仍是本机 SharedPreferences（v2 纪律：Key 不进 APK、不进 git、
/// 不上传；中转模式下 Key 存中转服务端）。三个 key 名与 v0.3.0 完全
/// 一致 —— 之前已在教练页填过 Key 的用户，升级后新入口直接读得到，
/// 不用重填。
class ModelConfigStore extends ChangeNotifier {
  ModelConfigStore();

  /// 三个存储 key —— **必须**与 v0.3.0 保持一致（用户存量 Key 的连续性）。
  static const String apiKeyKey = 'coach.api_key';
  static const String modelKey = 'coach.model';
  static const String endpointKey = 'coach.endpoint';

  /// 与当前 dsh 脚本同款模型（deepseek-v4-flash）。
  static const String defaultModel = 'deepseek-v4-flash';

  /// DeepSeek 官方直连端点。
  static const String defaultEndpoint =
      'https://api.deepseek.com/chat/completions';

  String _apiKey = '';
  String _model = defaultModel;
  String _endpoint = defaultEndpoint;

  /// 本机是否已存了 Key（卡片收起/展开状态的依据）。
  bool get keySaved => _apiKey.isNotEmpty;

  String get model => _model;

  String get endpoint => _endpoint;

  /// 生效配置（与 v0.3.0 规则一致：局域网中转地址 → server 模式）。
  ApiConfig get effective => buildConfig(_apiKey, _model, _endpoint);

  /// 从本机读回配置。
  ///
  /// try/catch 原因：测试环境没有 SharedPreferences 插件
  /// （`MissingPluginException`）→ 当作未配置；屏幕表现与真机一致
  /// （未配置 = 走离线规则兜底）。
  Future<void> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = prefs.getString(apiKeyKey) ?? '';
      final model = prefs.getString(modelKey) ?? '';
      final endpoint = prefs.getString(endpointKey) ?? '';
      _apiKey = key;
      _model = model.isEmpty ? defaultModel : model;
      _endpoint = endpoint.isEmpty ? defaultEndpoint : endpoint;
    } catch (_) {
      // 无插件（测试/桌面环境）→ 保持「未配置」。
    }
    notifyListeners();
  }

  /// 保存配置到本机。调用方随后即可从 [keySaved]/[effective] 读到新值。
  ///
  /// 先更新内存、再落盘（落盘失败只影响下次启动，不影响本次会话 ——
  /// 测试环境没有插件时走这个分支）；最后通知所有监听方（教练页/设置页）。
  Future<void> save({
    required String apiKey,
    String? model,
    String? endpoint,
  }) async {
    _apiKey = apiKey.trim();
    _model = (model ?? '').trim().isEmpty ? defaultModel : (model ?? '').trim();
    _endpoint = (endpoint ?? '').trim().isEmpty
        ? defaultEndpoint
        : (endpoint ?? '').trim();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(apiKeyKey, _apiKey);
      await prefs.setString(modelKey, _model);
      await prefs.setString(endpointKey, _endpoint);
    } catch (_) {
      // 无插件（测试环境）→ 只更新内存，不抛（真机一定可用）。
    }
    notifyListeners();
  }

  /// 由三个值构造 [ApiConfig]（v0.3.0 教练页 `_buildConfig` 的语义）。
  ApiConfig buildConfig(String key, String model, String endpoint) {
    final effectiveModel = model.isEmpty ? defaultModel : model;
    final effectiveEndpoint = endpoint.isEmpty ? defaultEndpoint : endpoint;
    return ApiConfig(
      endpoint: effectiveEndpoint,
      apiKey: key,
      model: effectiveModel,
      // 局域网中转地址（http://）→ server 模式（Key 存中转侧）；
      // 官方 https 端点 → 直连（Key 存本机）。
      mode: effectiveEndpoint.startsWith('http://')
          ? ProxyMode.server
          : ProxyMode.direct,
    );
  }
}
