import 'dart:convert';
import 'dart:io';

/// 线上视觉模型客户端（DeepSeek，OpenAI 兼容格式）。
///
/// 已验证事实（2026-09-20 查官方文档）：
/// - base_url: https://api.deepseek.com ，接口 POST /chat/completions
/// - 视觉能力由 Flash 系提供（文档写 `deepseek-flash`；`deepseek-v4-flash-vision-exp`
///   已下线，旧名仍可调用，请求由最新 Flash 承接）。
/// - 图片用 content block 数组传入，支持 base64 data URL。
///   来源: https://api-docs.deepseek.com/zh-cn/guides/vision
/// - 为了模型名以后变了不用重新发版，模型名/接口地址都放在这里可注入。
///   v2 默认 `deepseek-v4-flash`（和当前 dsh 同款，教练页可改）。
///
/// Key 存放（2026-09 用户拍板，v2 决策）：自用 App，Key **在手机里输入**
/// （教练页「模型配置」卡）→ 只存本机 SharedPreferences，
/// 不打进 APK、不进 git、不上传。因此：
///   1) [ProxyMode.direct]：默认路径 —— 直连官方接口，Key 在本机（个人自用）
///   2) [ProxyMode.server]：可选中转 —— Key 放中转侧（把接口地址填成
///      局域网 http:// 时客户端自动切这个模式），适合以后分发给他人用
/// 若将来公开分发本 App：必须改走中转，别直连（客户端 Key 可被反编译提取）。
enum ProxyMode { server, direct }

class ApiConfig {
  const ApiConfig({
    required this.endpoint,
    required this.apiKey,
    this.model = 'deepseek-v4-flash',
    this.mode = ProxyMode.server,
    this.timeout = const Duration(seconds: 30),
  });

  /// 服务端模式填中转地址；直连模式填 https://api.deepseek.com/chat/completions
  final String endpoint;
  final String apiKey;

  /// 模型名可注入，不写死在逻辑里。
  final String model;
  final ProxyMode mode;
  final Duration timeout;

  /// 直连且没 key → 直接判定不可用，走本地兜底。
  bool get isUsable =>
      endpoint.isNotEmpty && (mode == ProxyMode.server || apiKey.isNotEmpty);
}

class LlmException implements Exception {
  LlmException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;
  @override
  String toString() => 'LlmException($statusCode): $message';
}

/// 一次调用的结果：模型原始文本 + 解析出的 JSON（可能为 null）。
class LlmRawResult {
  const LlmRawResult({required this.text, this.decodedJson});
  final String text;
  final Object? decodedJson;
}

class VisionLlmClient {
  VisionLlmClient({required this.config, HttpClient? httpClient})
      : _http = httpClient ?? HttpClient();

  final ApiConfig config;
  final HttpClient _http;

  Future<LlmRawResult> analyzeImage({
    required String dataUrl,
    required String prompt,
    String mimeType = 'image/jpeg',
  }) async {
    final body = jsonEncode({
      'model': config.model,
      'messages': [
        {'role': 'system', 'content': prompt},
        {
          'role': 'user',
          'content': [
            {'type': 'text', 'text': '这是用户提供的参考图，请按要求输出建议 JSON。'},
            {'type': 'image_url', 'image_url': {'url': dataUrl}},
          ],
        },
      ],
      // 强制 JSON 输出，减少解析失败
      'response_format': {'type': 'json_object'},
      'stream': false,
    });

    final text = await _post(body);
    return LlmRawResult(text: text, decodedJson: extractJson(text));
  }

  Future<String> _post(String body) async {
    final uri = Uri.parse(config.endpoint);
    final req = await _http.postUrl(uri).timeout(config.timeout);
    req.headers.contentType = ContentType('application', 'json', charset: 'utf-8');
    if (config.apiKey.isNotEmpty) {
      req.headers.set(HttpHeaders.authorizationHeader, 'Bearer ${config.apiKey}');
    }
    req.add(utf8.encode(body));

    final res = await req.close().timeout(config.timeout);
    // ⚠️ 读响应体也必须带超时：上面那句只覆盖「连上 + 拿到响应头」。
    // `join()` 本身是**无限等**的 —— 坏服务器/弱网只要先回 200 头再慢慢挤字节
    // （或者干脆吊着不动），这里就永远不返回 → 页面的 finally 不执行 →
    // `_running` 永远是 true → 所有分析按钮永久变灰、且没有任何提示，
    // 用户只能杀进程。实测可复现（见 test/llm_and_compressor_test.dart
    // 的「读响应体超时（卡住的服务器）」组）。
    final resBody = await res
        .transform(utf8.decoder)
        .join()
        .timeout(config.timeout,
            onTimeout: () => throw LlmException(
                '读取响应超时（${config.timeout.inSeconds} 秒）'));
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw LlmException(
        'HTTP ${res.statusCode}: ${resBody.length > 400 ? resBody.substring(0, 400) : resBody}',
        statusCode: res.statusCode,
      );
    }

    final decoded = jsonDecode(resBody);
    if (decoded is! Map) {
      throw LlmException('响应不是 JSON 对象');
    }
    // OpenAI 兼容格式：choices[0].message.content
    final choices = decoded['choices'];
    if (choices is List && choices.isNotEmpty) {
      final first = choices.first;
      if (first is Map) {
        final msg = first['message'];
        if (msg is Map && msg['content'] is String) {
          return msg['content'] as String;
        }
        if (first['text'] is String) return first['text'] as String;
      }
    }
    throw LlmException('响应里找不到文本内容');
  }

  void close() => _http.close(force: true);
}

/// 从模型文本里抠出 JSON 对象。
///
/// 模型经常包一层 ```json ... ``` 或前后带解释文字，这里做容错。
/// 返回 null 表示抠不出来（调用方走兜底）。
///
/// **参数穷举做过 TDD**（见 `test/extract_json_param_test.dart`，35 个用例）。
/// 这个函数的参数是模型给的任意文本，必须假定它是**畸形/截断/对抗性**的。
/// 修过的 3 个 bug：
/// 1. `'{} }'` 这种括号不平衡的输入被当成解析成功（扫到第一个平衡就返回，
///    不管后面还有没有多余的 `}`）
/// 2. （已证伪）曾经怀疑"深嵌套被 jsonDecode 卡住"，实测 `jsonDecode`
///    能处理 5000 层合法嵌套 —— 当时那个失败**是我测试构造错了**
///    （`{{{"a":1}}}` 本来就不是合法 JSON）。这条记下来当反面教材：
///    测试挂了先怀疑测试自己。
/// 3. 多个候选块时，第一个块解析失败就整段放弃，不去试后面的
Object? extractJson(String text) {
  final trimmed = text.trim();
  if (trimmed.isEmpty) return null;

  // 1) 直接试
  final direct = _tryDecode(trimmed);
  if (direct != null) return direct;

  // 2) 去掉 markdown 代码围栏 —— **每个**围栏块都试，不因为第一个坏就放弃
  final fenced = RegExp(r'```(?:json)?\s*([\s\S]*?)```', caseSensitive: false)
      .allMatches(trimmed);
  for (final m in fenced) {
    final inner = m.group(1)?.trim();
    if (inner == null || inner.isEmpty) continue;
    final d = _tryDecode(inner) ?? _scanBalancedObject(inner);
    if (d != null) return d;
  }

  // 3) 扫描平衡的 {...}
  return _scanBalancedObject(trimmed);
}

/// 从 [text] 里扫出**完整且平衡**的 JSON 对象，返回能解析成功的那个。
///
/// 为什么要"从每个 `{` 都试一遍"：
/// 模型输出里**经常**前面有一坨坏内容、后面才是好的 JSON，例如：
/// ```
/// ```json
/// {坏掉了
/// ```
/// 还有这个：
/// {"good":true}
/// ```
/// 只试第一个 `{` 就会整段放弃 —— 实测就是这样漏掉了好数据。
///
/// 「平衡」的判定：
///   · 括号深度回到 0
///   · **字符串状态已闭合**（否则 `"没闭合` 会被误判成结束）
String? _findBalancedObject(String text) {
  // 逐个 `{` 起点试。用 while 而不是一次性 indexOf。
  var searchFrom = 0;
  while (true) {
    final start = text.indexOf('{', searchFrom);
    if (start < 0) return null;
    final candidate = _balancedFrom(text, start);
    if (candidate != null && _tryDecode(candidate) != null) {
      return candidate;
    }
    // 这个起点不行，从下一个字符继续找
    searchFrom = start + 1;
  }
}

/// 从 [start]（必须是 `{`）开始，找出**该位置**起的平衡对象片段。
/// 找不到（截断/未闭合字符串）返回 null。
String? _balancedFrom(String text, int start) {
  var depth = 0;
  var inString = false;
  var escaped = false;

  for (var i = start; i < text.length; i++) {
    final c = text[i];
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (c.codeUnitAt(0) == 0x5C) {
        escaped = true; // 反斜杠：转义下一个字符
      } else if (c == '"') {
        inString = false;
      }
      continue;
    }
    if (c == '"') {
      inString = true;
    } else if (c == '{') {
      depth++;
    } else if (c == '}') {
      depth--;
      if (depth < 0) return null; // 多余的右括号：不是合法对象
      if (depth == 0) {
        if (inString) continue; // 字符串还没闭合，继续找
        // ⚠️ 这里**不要**检查"后面还有没有多余的 }"。
        // 我第一版加了那个检查，把正常情况也拒了：
        //   `'{"a":1}}'`         —— 解析出 {"a":1}，后面 } 是噪声
        //   `'```json\n{"a":1}'`  —— 围栏没闭合，后面还有反引号
        // 「截断/带噪声」是模型输出的常态，容错比严格重要。
        return text.substring(start, i + 1);
      }
    }
  }
  // 扫完了深度没归零（或字符串没闭合）→ 截断，不是合法对象
  return null;
}

Object? _scanBalancedObject(String text) {
  // 先直接试整段（可能是纯 JSON）
  final direct = _tryDecode(text);
  if (direct != null) return direct;
  // 再扫出第一个平衡对象
  final candidate = _findBalancedObject(text);
  if (candidate == null) return null;
  return _tryDecode(candidate);
}

Object? _tryDecode(String s) {
  try {
    return jsonDecode(s);
  } catch (_) {
    return null;
  }
}


