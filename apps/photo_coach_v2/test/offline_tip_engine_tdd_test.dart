import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:photo_coach_v2/features/coach/analyzer.dart';
import 'package:photo_coach_v2/features/coach/image_compressor.dart';
import 'package:photo_coach_v2/features/coach/llm_client.dart';
import 'package:photo_coach_v2/features/coach/offline_tip_engine.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';

/// OfflineTipEngine 的 TDD 测试。
///
/// **这个文件是「测试先行」写出来的** —— 先写测试、看它红，再改实现让它绿。
///
/// 背景：这个引擎虽然行覆盖 100%，但那只是"代码被执行过"。
/// 「用户实际看到什么」这一层完全没被测过。它的 `reason` 参数被直接
/// 拼进用户可见的 tips 里，而调用方传进去的往往是**技术错误原文**：
///   · analyzer 传 `'HTTP 500: server error'`
///   · 网络异常传 `'SocketException: Failed host lookup'`
///   · 没配 key 传 `'no_api_config'`
/// 于是用户在"给建议"卡片里看到一串英文异常 —— 这不是人话。
///
/// 这个测试锁住：**离线提示必须是给人看的，不许把技术错误原文端上来。**

void main() {
  // 真机实测过的失败（人类 2026-09-21 截图）：手机开着 VPN/代理时，
  // 端点是通的、权限也有，但 **TLS 握手被打断**。那时候给用户的提示
  // 是"AI 服务暂时不可用" —— 完全没法动手。这几条锁死"必须可操作"。
  group('网络层失败要说人话、要能动手（实机回归）', () {
    test('TLS 握手失败 → 提示关 VPN/代理或换网络，而不是"暂时不可用"', () {
      final s = const OfflineTipEngine().suggest(
        reason: 'AI 服务暂时不可用',
        detail: 'HandshakeException: Connection terminated during handshake',
      );
      final line = s.tips.first;
      expect(line, contains('加密握手'));
      expect(line, anyOf(contains('VPN'), contains('代理')));
      expect(line, contains('再试'));
      expect(line, isNot(contains('暂时不可用')));
    });

    test('找不到服务器（DNS）→ 提示检查网络或关代理', () {
      final s = const OfflineTipEngine().suggest(
        reason: 'AI 服务暂时不可用',
        detail: 'SocketException: Failed host lookup: api.deepseek.com',
      );
      expect(s.tips.first, contains('找不到服务器'));
    });

    test('异常原文（英文）不许流到用户可见文案里', () {
      final s = const OfflineTipEngine().suggest(
        reason: 'AI 服务暂时不可用',
        detail: 'HandshakeException: Connection terminated during handshake',
      );
      for (final t in s.tips) {
        expect(t, isNot(contains('HandshakeException')));
        expect(t, isNot(contains('Connection terminated')));
      }
      // 但技术细节要留一份给排查
      expect(s.errorCode, contains('HandshakeException'));
    });
  });

  const engine = OfflineTipEngine();

  group('离线兜底 —— 基本契约（诚实性）', () {
    test('source 必须是 ruleFallback，绝不能冒充 AI', () {
      final s = engine.suggest();
      expect(s.source, SuggestionSource.ruleFallback);
      expect(s.source, isNot(SuggestionSource.visionModel));
    });

    test('一定要给出可执行的建议，不能是空壳', () {
      final s = engine.suggest();
      expect(s.tips, isNotEmpty, reason: '一条建议都不给，用户点完一脸懵');
      expect(s.cameraMove.hint.trim(), isNotEmpty);
      expect(s.composition.rule, isNotEmpty);
    });

    test('每条 tip 都是人话：非空、不太长、不含换行', () {
      final s = engine.suggest();
      for (final t in s.tips) {
        expect(t.trim(), isNotEmpty, reason: '空 tip 会渲染成空白行');
        expect(t.contains('\n'), isFalse, reason: 'tip 里不该有换行');
        expect(t.length, lessThanOrEqualTo(60),
            reason: 'tip 太长会被截断：「$t」');
      }
    });

    test('不可变：两次调用互不影响（没有共享可变状态）', () {
      final a = engine.suggest(reason: 'HTTP 500');
      final b = engine.suggest();
      expect(a.tips, isNot(same(b.tips)));
      // b 不该被 a 污染
      expect(b.tips.any((t) => t.contains('500')), isFalse);
    });
  });

  group('离线兜底 —— 不把技术错误原文给用户（TDD 的核心用例）', () {
    test('HTTP 错误码不许原样出现在提示里', () {
      final s = engine.suggest(reason: 'HTTP 500: server error');
      final all = s.tips.join(' ');
      expect(all.contains('HTTP'), isFalse,
          reason: '用户不需要知道 HTTP 状态码，这是技术噪音');
      expect(all.contains('500'), isFalse);
      expect(all.contains('server error'), isFalse);
    });

    test('SocketException / 堆栈这类东西不许出现', () {
      final s = engine.suggest(
          reason: 'SocketException: Failed host lookup: api.deepseek.com');
      final all = s.tips.join(' ');
      expect(all.contains('SocketException'), isFalse);
      expect(all.contains('Exception'), isFalse);
      expect(all.contains('deepseek'), isFalse);
    });

    test('内部代号（no_api_config 等）不许直接给用户看', () {
      for (final code in [
        'no_api_config',
        'unparsable_model_output',
        'timeout',
        'empty_response',
      ]) {
        final s = engine.suggest(reason: code);
        final all = s.tips.join(' ');
        expect(all.contains(code), isFalse,
            reason: '内部代号「$code」不该原样展示');
      }
    });

    test('但**仍然要告诉用户"这是离线结果"**（诚实，不能因为怕露技术细节就不说）', () {
      final s = engine.suggest(reason: 'HTTP 500');
      final all = s.tips.join(' ');
      expect(
        all.contains('离线') || all.contains('本地') || all.contains('没接上'),
        isTrue,
        reason: '必须让用户知道这不是 AI 分析出来的结果',
      );
    });

    test('技术细节不该丢：通过 errorCode 保留，便于排查', () {
      final s = engine.suggest(reason: 'HTTP 500: server error');
      // 细节要留在结构化字段里（给开发者/日志看），只是不进用户可见文案
      expect(s.errorCode, isNotNull);
      expect(s.errorCode, contains('500'));
    });

    test('没传 reason 时不出现"为什么走离线"这类多余的话', () {
      final s = engine.suggest();
      final all = s.tips.join(' ');
      expect(all.contains('为什么'), isFalse,
          reason: '没有原因是正常的（用户就没配模型），不该当异常说');
    });

    test('中文原因可以原样带出（它本来就是给人看的）', () {
      final s = engine.suggest(reason: '这台设备没联网');
      final all = s.tips.join(' ');
      expect(all.contains('这台设备没联网'), isTrue);
    });
  });

  group('离线兜底 —— 建议本身要靠谱（内容质量）', () {
    test('构图规则是三分法（离线只敢给这条通用原则）', () {
      expect(engine.suggest().composition.rule, 'rule_of_thirds');
    });

    test('明确说明曝光没有数据依据，不许编一个数', () {
      final s = engine.suggest();
      expect(s.exposure.reason, isNotEmpty);
      expect(s.exposure.reason, contains('没有'),
          reason: '必须承认没有测光数据，不能假装测了');
    });

    test('建议条数适中（3–5 条），太少没用、太多看不过来', () {
      final s = engine.suggest();
      expect(s.tips.length, inInclusiveRange(3, 5));
    });

    test('tips 不重复', () {
      final s = engine.suggest(reason: 'HTTP 500');
      expect(s.tips.toSet().length, s.tips.length, reason: '有重复的建议');
    });
  });

  // ---------------------------------------------------------------------
  // 第二轮 TDD（RED）：analyzer 走兜底时，必须把**真实错误码**带进 errorCode，
  // 否则排查时只看到一句"线上模型调用失败"，不知道到底是 500 还是超时。
  // ---------------------------------------------------------------------

  group('analyzer 兜底时保留真实错误码（第二轮 TDD）', () {
    test('HTTP 500 时，suggestion.errorCode 要含 500', () async {
      final http = FakeHttpClient(statusCode: 500, responseBody: 'server error');
      final result = await SuggestionAnalyzer(
        config: const ApiConfig(
          endpoint: 'https://fake.local/chat/completions',
          apiKey: 'sk-test',
          mode: ProxyMode.direct,
        ),
        client: VisionLlmClient(
          config: const ApiConfig(
            endpoint: 'https://fake.local/chat/completions',
            apiKey: 'sk-test',
            mode: ProxyMode.direct,
          ),
          httpClient: http,
        ),
      ).analyzePayload(const ImageCompressor().compressBytes(_png()));

      expect(result.usedFallback, isTrue);
      expect(result.suggestion.errorCode, isNotNull,
          reason: '兜底建议必须保留技术原因，否则没法排查');
      expect(result.suggestion.errorCode, contains('500'),
          reason: '要能看到真实的 HTTP 状态码，实际：'
              '${result.suggestion.errorCode}');
    });

    test('用户可见的 tips 里仍然不许出现 HTTP 500（人话优先）', () async {
      final http = FakeHttpClient(statusCode: 500, responseBody: 'server error');
      final result = await SuggestionAnalyzer(
        config: const ApiConfig(
          endpoint: 'https://fake.local/chat/completions',
          apiKey: 'sk-test',
          mode: ProxyMode.direct,
        ),
        client: VisionLlmClient(
          config: const ApiConfig(
            endpoint: 'https://fake.local/chat/completions',
            apiKey: 'sk-test',
            mode: ProxyMode.direct,
          ),
          httpClient: http,
        ),
      ).analyzePayload(const ImageCompressor().compressBytes(_png()));

      final all = result.suggestion.tips.join(' ');
      expect(all.contains('HTTP'), isFalse,
          reason: '技术细节只能进 errorCode，不能进 tips');
      expect(all.contains('500'), isFalse);
    });

    test('技术细节不能只在 warnings 里（那是给开发者面板看的）', () async {
      // warnings 面向"解析提示"面板，errorCode 面向链路排查，两者都要有
      final http = FakeHttpClient(throwOnRequest: true);
      final result = await SuggestionAnalyzer(
        config: const ApiConfig(
          endpoint: 'https://fake.local/chat/completions',
          apiKey: 'sk-test',
          mode: ProxyMode.direct,
        ),
        client: VisionLlmClient(
          config: const ApiConfig(
            endpoint: 'https://fake.local/chat/completions',
            apiKey: 'sk-test',
            mode: ProxyMode.direct,
          ),
          httpClient: http,
        ),
      ).analyzePayload(const ImageCompressor().compressBytes(_png()));

      expect(result.suggestion.errorCode, isNotNull);
      expect(result.warnings, isNotEmpty);
    });
  });
}

Uint8List _png() {
  final image = img.Image(width: 16, height: 16);
  img.fill(image, color: img.ColorRgb8(120, 140, 160));
  return Uint8List.fromList(img.encodePng(image));
}


/// 最小的假 HTTP 客户端（跟 analyzer_test.dart 里的同类，这里自带一份，
/// 避免测试之间互相依赖）。
class FakeHttpClient implements HttpClient {
  FakeHttpClient({
    this.responseBody = '',
    this.statusCode = 200,
    this.throwOnRequest = false,
  });

  final String responseBody;
  final int statusCode;
  final bool throwOnRequest;

  @override
  Future<HttpClientRequest> postUrl(Uri url) async {
    if (throwOnRequest) {
      throw const SocketException('测试：故意断网');
    }
    return _FakeRequest(this);
  }

  @override
  void close({bool force = false}) {}

  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class _FakeRequest implements HttpClientRequest {
  _FakeRequest(this.client);
  final FakeHttpClient client;
  final _body = BytesBuilder();

  @override
  HttpHeaders get headers => _FakeHeaders();

  @override
  void add(List<int> data) => _body.add(data);

  @override
  Future<HttpClientResponse> close() async =>
      _FakeResponse(client.statusCode, client.responseBody);

  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class _FakeHeaders implements HttpHeaders {
  @override
  ContentType? contentType;
  @override
  void set(String name, Object value, {bool preserveHeaderCase = false}) {}
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class _FakeResponse extends Stream<List<int>> implements HttpClientResponse {
  _FakeResponse(this.statusCode, this.body);
  @override
  final int statusCode;
  final String body;
  @override
  StreamSubscription<List<int>> listen(
    void Function(List<int> event)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) =>
      Stream<List<int>>.fromIterable([utf8.encode(body)]).listen(onData,
          onError: onError, onDone: onDone, cancelOnError: cancelOnError);
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}
