import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:photo_coach_v2/features/coach/image_compressor.dart';
import 'package:photo_coach_v2/features/coach/llm_client.dart';
import 'package:photo_coach_v2/features/coach/offline_tip_engine.dart';
import 'package:photo_coach_v2/features/coach/prompt.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';

void main() {
  group('extractJson —— 模型输出反正是文本，得抠出 JSON', () {
    test('纯 JSON 直接解析', () {
      final j = extractJson('{"a":1}');
      expect(j, isA<Map>());
      expect((j! as Map)['a'], 1);
    });

    test('带 ```json 代码围栏', () {
      final j = extractJson('```json\n{"rule":"x"}\n```');
      expect((j! as Map)['rule'], 'x');
    });

    test('前后带解释文字', () {
      final j = extractJson('好的，这是我的建议：\n{"ev": -0.3}\n希望有帮助！');
      expect((j! as Map)['ev'], -0.3);
    });

    test('嵌套对象取外层完整括号', () {
      final j = extractJson('{"a":{"b":{"c":1}},"d":2}');
      expect((j! as Map)['d'], 2);
    });

    test('字符串里的花括号不会误判', () {
      final j = extractJson('{"hint":"往前 {这里} 走","n":1}')! as Map;
      expect(j['n'], 1);
      expect(j['hint'], '往前 {这里} 走');
    });

    test('转义引号不会破坏扫描', () {
      final j = extractJson('{"t":"他说 \\"你好\\" 了","n":2}');
      expect((j! as Map)['n'], 2);
    });

    test('没有 JSON 就返回 null（交给兜底）', () {
      expect(extractJson('抱歉，我看不清这张图。'), isNull);
      expect(extractJson(''), isNull);
      expect(extractJson('   '), isNull);
    });
  });

  group('ImageCompressor —— 省 token / 省流量', () {
    Uint8List makePng(int w, int h) {
      final image = img.Image(width: w, height: h);
      img.fill(image, color: img.ColorRgb8(120, 30, 200));
      return Uint8List.fromList(img.encodePng(image));
    }

    test('超长边会被压到 maxSide 以内', () {
      const compressor = ImageCompressor(maxSide: 256, quality: 80);
      final payload = compressor.compressBytes(makePng(1024, 512));

      expect(payload.compressed, isTrue);
      expect(payload.mimeType, 'image/jpeg');
      expect(payload.width, 256);
      expect(payload.height, 128);
      expect(payload.byteSize, greaterThan(0));
    });

    test('本来就小就不放大（避免白白糊图）', () {
      const compressor = ImageCompressor(maxSide: 1024);
      final payload = compressor.compressBytes(makePng(200, 100));
      expect(payload.width, 200);
      expect(payload.height, 100);
    });

    test('非图片数据走原图直通，不抛异常', () {
      const compressor = ImageCompressor();
      final payload =
          compressor.compressBytes(Uint8List.fromList([1, 2, 3, 4, 5]));
      expect(payload.compressed, isFalse);
      expect(payload.byteSize, 5);
    });

    test('toDataUrl 产出合法 base64 data URL', () {
      const compressor = ImageCompressor(maxSide: 64);
      final payload = compressor.compressBytes(makePng(64, 64));
      final url = payload.toDataUrl();
      expect(url.startsWith('data:image/jpeg;base64,'), isTrue);
      final b64 = url.split(',').last;
      expect(base64Decode(b64).length, payload.byteSize);
    });
  });

  group('ApiConfig 可用性判定', () {
    test('直连但没 key → 不可用（不许发无鉴权请求）', () {
      const c = ApiConfig(
        endpoint: 'https://api.deepseek.com/chat/completions',
        apiKey: '',
        mode: ProxyMode.direct,
      );
      expect(c.isUsable, isFalse);
    });

    test('直连且有 key → 可用', () {
      const c = ApiConfig(
        endpoint: 'https://api.deepseek.com/chat/completions',
        apiKey: 'sk-test',
        mode: ProxyMode.direct,
      );
      expect(c.isUsable, isTrue);
    });

    test('服务端中转不需要客户端 key', () {
      const c = ApiConfig(
        endpoint: 'https://my-proxy.example.com/analyze',
        apiKey: '',
        mode: ProxyMode.server,
      );
      expect(c.isUsable, isTrue);
    });

    test('默认模型名是 deepseek-v4-flash（vision-exp 已下线，v2 换成 v4-flash）', () {
      const c = ApiConfig(endpoint: 'x', apiKey: 'y');
      expect(c.model, 'deepseek-v4-flash');
    });

    test('端点为空的直连配置不可用', () {
      const c = ApiConfig(endpoint: '', apiKey: 'sk-x');
      expect(c.isUsable, isFalse);
    });
  });

  group('提示词契约', () {
    test('内置提示词要求只输出 JSON 且带 schema_version', () {
      final p = CompositionPrompt.defaultPrompt;
      expect(p.contains('schema_version'), isTrue);
      expect(p.contains('只输出一个 JSON'), isTrue);
      expect(p.contains('current_box'), isTrue);
      expect(p.contains('target_box'), isTrue);
    });

    test('内置提示词的字段名与解析器一致（防止改一边忘另一边）', () {
      final p = CompositionPrompt.defaultPrompt;
      for (final key in [
        'composition',
        'subject',
        'camera_move',
        'pan_deg',
        'tilt_deg',
        'dolly_m',
        'zoom',
        'exposure',
        'ev',
        'tips',
      ]) {
        expect(p.contains(key), isTrue, reason: '提示词缺字段 $key');
      }
    });

    test('远端提示词优先，空则回退内置', () {
      expect(CompositionPrompt.resolve('自定义'), '自定义');
      expect(CompositionPrompt.resolve('  '), CompositionPrompt.defaultPrompt);
      expect(CompositionPrompt.resolve(null), CompositionPrompt.defaultPrompt);
    });
  });

  group('OfflineTipEngine —— 兜底必须自报家门', () {
    test('产出的建议明确标记为本地规则，不冒充 AI', () {
      const engine = OfflineTipEngine();
      final s = engine.suggest(reason: '没网');
      expect(s.source, SuggestionSource.ruleFallback);
      expect(s.source.label.contains('本地规则'), isTrue);
      expect(s.tips.any((t) => t.contains('没网')), isTrue);
    });

    test('兜底也给出可执行的构图建议，不是空壳', () {
      const engine = OfflineTipEngine();
      final s = engine.suggest();
      expect(s.composition.rule, 'rule_of_thirds');
      expect(s.cameraMove.hint, isNotEmpty);
      expect(s.tips.length, greaterThanOrEqualTo(3));
    });
  });

  // =====================================================================
  // 卡住的服务器：读响应体不能无限等
  //
  // **为什么必须有这条**：`config.timeout` 只覆盖到「连上 + 拿到响应头」，
  // 之后的 `res.transform(utf8.decoder).join()` 是**无限等**的。
  // 弱网/坏服务器只要先回 200 头、再慢慢挤字节（或者干脆不动），
  // 分析就永远不返回 → 页面的 `finally` 不执行 → `_running` 永远是 true
  // → 所有分析按钮永久变灰，没有任何提示，只能杀进程。
  // =====================================================================
  group('读响应体超时（卡住的服务器）', () {
    test('服务器回了响应头就不动了 → 必须抛超时，不能永久卡住', () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      addTearDown(() => server.close(force: true));

      server.listen((req) async {
        req.response.headers.contentType = ContentType.json;
        // 只写半截 JSON，然后**故意不 close** —— 模拟"吊着不动的服务器"
        req.response.write('{"choices":[{"message":{"content":"好');
        await req.response.flush();
      });

      final client = VisionLlmClient(
        config: ApiConfig(
          endpoint: 'http://127.0.0.1:${server.port}/analyze',
          apiKey: 'test-key',
          mode: ProxyMode.server,
          timeout: const Duration(milliseconds: 400),
        ),
      );
      addTearDown(client.close);

      await expectLater(
        client.analyzeImage(
          dataUrl: 'data:image/jpeg;base64,AAAA',
          prompt: '测试',
        ),
        throwsA(isA<LlmException>()),
      );
    });

    test('正常响应不能被超时误伤', () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      addTearDown(() => server.close(force: true));

      server.listen((req) async {
        req.response.headers.contentType = ContentType.json;
        req.response.write(jsonEncode({
          'choices': [
            {
              'message': {'content': '{"tips":["ok"]}'}
            }
          ]
        }));
        await req.response.close();
      });

      final client = VisionLlmClient(
        config: ApiConfig(
          endpoint: 'http://127.0.0.1:${server.port}/analyze',
          apiKey: 'test-key',
          mode: ProxyMode.server,
          timeout: const Duration(seconds: 5),
        ),
      );
      addTearDown(client.close);

      final r = await client.analyzeImage(
        dataUrl: 'data:image/jpeg;base64,AAAA',
        prompt: '测试',
      );
      expect(r.text, contains('tips'));
    });
  });
}
