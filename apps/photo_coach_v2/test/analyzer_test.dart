import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:photo_coach_v2/features/coach/analyzer.dart';
import 'package:photo_coach_v2/features/analysis/body_facts.dart';
import 'package:photo_coach_v2/features/poses/pose.dart';
import 'package:photo_coach_v2/features/coach/image_compressor.dart';
import 'package:photo_coach_v2/features/coach/llm_client.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';

/// 假 HTTP 客户端：不发真请求，按预设返回。
/// （零信任：验证编排器的**降级行为**，不需要真联网。）
class FakeHttpClient implements HttpClient {
  FakeHttpClient({this.responseBody = '', this.statusCode = 200, this.throwOnRequest = false});

  final String responseBody;
  final int statusCode;
  final bool throwOnRequest;

  /// 记录发出去的请求体，用来断言「图片确实被压过再上传」。
  final List<String> sentBodies = [];

  @override
  Future<HttpClientRequest> postUrl(Uri url) async {
    if (throwOnRequest) {
      throw const SocketException('模拟断网');
    }
    return _FakeRequest(this);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError(
      '测试用假客户端不支持 ${invocation.memberName}');

  @override
  void close({bool force = false}) {}
}

class _FakeRequest implements HttpClientRequest {
  _FakeRequest(this._client);

  final FakeHttpClient _client;
  final _body = BytesBuilder();

  @override
  HttpHeaders get headers => _FakeHeaders();

  @override
  void add(List<int> data) => _body.add(data);

  @override
  Future<HttpClientResponse> close() async {
    final text = utf8.decode(_body.takeBytes());
    _client.sentBodies.add(text);
    return _FakeResponse(_client.statusCode, _client.responseBody);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('不支持 ${invocation.memberName}');
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
  }) {
    return Stream<List<int>>.fromIterable([utf8.encode(body)]).listen(
      onData,
      onError: onError,
      onDone: onDone,
      cancelOnError: cancelOnError,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('不支持 ${invocation.memberName}');
}

Uint8List tinyPng() {
  final image = img.Image(width: 800, height: 600);
  img.fill(image, color: img.ColorRgb8(10, 200, 90));
  return Uint8List.fromList(img.encodePng(image));
}

/// 造一个 OpenAI 兼容的响应体。
String openAiBody(String content) => jsonEncode({
      'choices': [
        {
          'message': {'role': 'assistant', 'content': content}
        }
      ]
    });

void main() {
  const goodJson = '''
{
  "schema_version": "1.0",
  "composition": {"rule":"rule_of_thirds","confidence":0.9,"horizon_tilt_deg":0},
  "subject": {"label":"person","current_box":[0.4,0.3,0.2,0.5],"target_box":[0.33,0.25,0.2,0.5]},
  "camera_move": {"pan_deg":-6,"tilt_deg":2,"dolly_m":0,"zoom":1.0,"hint":"向左一点"},
  "exposure": {"ev":-0.3,"reason":"高光过曝"},
  "tips": ["主体放三分之一线"]
}''';

  ApiConfig config() => const ApiConfig(
        endpoint: 'https://fake.local/chat/completions',
        apiKey: 'sk-fake',
        mode: ProxyMode.direct,
      );

  SuggestionAnalyzer build(FakeHttpClient http) => SuggestionAnalyzer(
        config: config(),
        client: VisionLlmClient(config: config(), httpClient: http),
      );

  group('SuggestionAnalyzer —— 编排：压缩 → 模型 → 解析 → 兜底', () {
    test('模型返回合法 JSON：原样产出 AI 建议，标记不降级', () async {
      final http = FakeHttpClient(responseBody: openAiBody(goodJson));
      final payload = const ImageCompressor(maxSide: 1024).compressBytes(tinyPng());

      final result = await build(http).analyzePayload(payload);

      expect(result.usedFallback, isFalse);
      expect(result.isRemote, isTrue);
      expect(result.suggestion.source, SuggestionSource.visionModel);
      expect(result.suggestion.cameraMove.hint, '向左一点');
      expect(result.suggestion.exposure.ev, closeTo(-0.3, 1e-9));
      expect(result.warnings, isEmpty);
      expect(result.error, isNull);
      expect(result.elapsed, isNotNull);
    });

    test('带姿势分析：发给模型的提示词里**必须**含这个姿势（打通点）', () async {
      final http = FakeHttpClient(responseBody: openAiBody(goodJson));
      final payload = const ImageCompressor(maxSide: 1024).compressBytes(tinyPng());
      const pose = Pose(
        id: 'p1',
        title: '回头杀',
        category: '站姿',
        strokes: [PoseStroke(0.5, 0.2, 0.5, 0.6)],
        scene: '街拍',
        tips: ['肩膀放松', '下巴微收'],
      );

      await build(http).analyzePayload(payload, targetPose: pose);

      final body = http.sentBodies.single;
      expect(body, contains('回头杀'),
          reason: '姿势标题没进提示词 —— 那模型给的方案就不是针对这个姿势的');
      expect(body, contains('街拍'));
      expect(body, contains('肩膀放松'));
      expect(body, contains('拍摄方案必须服务于它'));
      expect(body, contains('subject_position'));
    });

    test('不带姿势分析：提示词里**不该**出现姿势段（别凭空塞）', () async {
      final http = FakeHttpClient(responseBody: openAiBody(goodJson));
      final payload = const ImageCompressor(maxSide: 1024).compressBytes(tinyPng());

      await build(http).analyzePayload(payload);

      expect(http.sentBodies.single, isNot(contains('拍摄方案必须服务于它')));
    });

    test('带端上测量值分析：请求体里**必须**含测量结果（打通点）', () async {
      final http = FakeHttpClient(responseBody: openAiBody(goodJson));
      final payload = const ImageCompressor(maxSide: 1024).compressBytes(tinyPng());
      const facts = BodyFacts(
        box: Rect01(0.4, 0.18, 0.2, 0.5),
        visibleCount: 11,
        eyeLineY: 0.18,
        shoulderTiltDeg: 18.4,
        lowerShoulder: '右',
        headTurnText: '头偏向画面右侧',
        bodySpanRatio: 0.45,
      );

      await build(http).analyzePayload(payload, bodyFacts: facts);

      final body = http.sentBodies.single;
      expect(body, contains('端上关键点测量值'),
          reason: '测量值没进请求体 —— 那模型还是在看图瞎猜');
      expect(body, contains('不要重新看图猜'));
      expect(body, contains('肩线倾斜'));
      expect(body, contains('18.4'));
    });

    test('不带测量值：提示词里不该出现那一段', () async {
      final http = FakeHttpClient(responseBody: openAiBody(goodJson));
      final payload = const ImageCompressor(maxSide: 1024).compressBytes(tinyPng());
      await build(http).analyzePayload(payload);
      expect(http.sentBodies.single, isNot(contains('端上关键点测量值')));
    });

    test('上传的是压缩后的图（长边 ≤ 1024），不是原图', () async {
      final http = FakeHttpClient(responseBody: openAiBody(goodJson));
      final payload = ImageCompressor(maxSide: 512)
          .compressBytes(tinyPng()); // 800x600 → 512x384

      await build(http).analyzePayload(payload);

      expect(http.sentBodies, hasLength(1));
      final sent = jsonDecode(http.sentBodies.single) as Map;
      // v1 迁移适配：v2 默认模型是 deepseek-v4-flash（用户拍板，教练页可改），
      // 断言跟着 v2 的默认走；用例本体（压缩图上传）不变。
      expect(sent['model'], 'deepseek-v4-flash');
      final content = (sent['messages'] as List)[1]['content'] as List;
      final url = content[1]['image_url']['url'] as String;
      final bytes = base64Decode(url.split(',').last);
      final decoded = img.decodeImage(bytes)!;
      expect(decoded.width, 512);
      expect(decoded.height, 384);
      expect(decoded.width, lessThan(800), reason: '不该原样上传');
    });

    test('模型回的是自然语言（抠不出 JSON）→ 降级 + 明确报错', () async {
      final http = FakeHttpClient(
          responseBody: openAiBody('这张图构图不错，建议把人物放左边。'));

      final result = await build(http)
          .analyzePayload(const ImageCompressor().compressBytes(tinyPng()));

      expect(result.usedFallback, isTrue);
      expect(result.isRemote, isFalse);
      expect(result.suggestion.source, SuggestionSource.ruleFallback);
      expect(result.error, 'unparsable_model_output');
      expect(result.warnings.any((w) => w.contains('无法解析')), isTrue);
    });

    test('模型返回 JSON 但缺字段 → 不降级，但要报警告', () async {
      final http = FakeHttpClient(
          responseBody: openAiBody('{"composition":{"rule":"centered"}}'));

      final result = await build(http)
          .analyzePayload(const ImageCompressor().compressBytes(tinyPng()));

      expect(result.usedFallback, isFalse);
      expect(result.suggestion.composition.rule, 'centered');
      expect(result.warnings, isNotEmpty);
    });

    test('HTTP 500 → 降级到离线规则，不抛异常给 UI', () async {
      final http = FakeHttpClient(statusCode: 500, responseBody: 'server error');

      final result = await build(http)
          .analyzePayload(const ImageCompressor().compressBytes(tinyPng()));

      expect(result.usedFallback, isTrue);
      expect(result.error, contains('500'));
      expect(result.suggestion.tips, isNotEmpty);
    });

    test('断网 → 降级到离线规则，不抛异常给 UI', () async {
      final http = FakeHttpClient(throwOnRequest: true);

      final result = await build(http)
          .analyzePayload(const ImageCompressor().compressBytes(tinyPng()));

      expect(result.usedFallback, isTrue);
      expect(result.suggestion.source, SuggestionSource.ruleFallback);
      expect(result.error, isNotNull);
    });

    test('没配 API → 直接离线，不浪费时间发请求', () async {
      final analyzer = SuggestionAnalyzer(
        config: const ApiConfig(endpoint: '', apiKey: ''),
      );

      final result = await analyzer
          .analyzePayload(const ImageCompressor().compressBytes(tinyPng()));

      expect(result.usedFallback, isTrue);
      expect(result.error, 'no_api_config');
      expect(result.suggestion.source, SuggestionSource.ruleFallback);
    });

    test('响应里没有 choices → 降级，不抛', () async {
      final http = FakeHttpClient(responseBody: jsonEncode({'foo': 'bar'}));

      final result = await build(http)
          .analyzePayload(const ImageCompressor().compressBytes(tinyPng()));

      expect(result.usedFallback, isTrue);
      expect(result.error, isNotNull);
    });

    test('响应不是 JSON → 降级，不抛', () async {
      final http = FakeHttpClient(responseBody: '<html>502</html>');

      final result = await build(http)
          .analyzePayload(const ImageCompressor().compressBytes(tinyPng()));

      expect(result.usedFallback, isTrue);
    });

    test('每次分析都带上了提示词（提示词不能丢）', () async {
      final http = FakeHttpClient(responseBody: openAiBody(goodJson));
      await build(http).analyzePayload(
          const ImageCompressor().compressBytes(tinyPng()));

      final sent = jsonDecode(http.sentBodies.single) as Map;
      final system = (sent['messages'] as List).first['content'] as String;
      expect(system.contains('target_box'), isTrue);
      expect(system.contains('schema_version'), isTrue);
    });
  });
}
