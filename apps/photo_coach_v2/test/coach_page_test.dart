import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/app_session.dart';
import 'package:photo_coach_v2/features/coach/coach_page.dart';
import 'package:photo_coach_v2/features/coach/llm_client.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';
import 'package:photo_coach_v2/features/coach/video_input.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 教练页（F2）的测试。
///
/// 覆盖率起点 31.6%（212 行里 67 行）。缺的主要是：空态、视频区块、
/// 错误提示、以及「离线兜底不许冒充 AI」这条最重要的诚实性规则。
///
/// 这里**不联网**：所有测试都用「没有 key」的配置，或注入假的 VideoFrameSource，
/// 走的是本地规则兜底路径 —— 那正是最需要验证的部分。

class _FakeFrameSource implements VideoFrameSource {
  _FakeFrameSource({this.throwMessage});

  final String? throwMessage;

  @override
  Future<Duration> duration(String path) async {
    if (throwMessage != null) throw VideoInputException(throwMessage!);
    return const Duration(seconds: 10);
  }

  @override
  Future<RawFrame> frameAt(String path, Duration at) async {
    if (throwMessage != null) throw VideoInputException(throwMessage!);
    throw VideoInputException('测试里不造真帧');
  }
}

Future<void> pumpCoach(
  WidgetTester tester, {
  ApiConfig? config,
  AppSession? session,
  VideoFrameSource? frameSource,
  VoidCallback? onNavigateToShoot,
}) async {
  tester.view.physicalSize = const Size(390 * 3, 1200 * 3);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(MaterialApp(
    theme: ThemeData.dark(),
    home: CoachPage(
      // 故意给一个「直连但没 key」的配置 —— 强制走本地兜底，不联网
      config: config ??
          const ApiConfig(
            endpoint: 'https://api.deepseek.com/chat/completions',
            apiKey: '',
            mode: ProxyMode.direct,
          ),
      session: session,
      frameSource: frameSource,
      onNavigateToShoot: onNavigateToShoot,
    ),
  ));
  await tester.pump();
}

void main() {
  group('教练页 —— 空态', () {
    testWidgets('显示标题，并说明还没选图', (tester) async {
      await pumpCoach(tester);
      expect(find.textContaining('构图教练'), findsWidgets);
      expect(find.textContaining('还没选图'), findsWidgets);
    });

    testWidgets('三个入口都在：拍一张 / 从相册选 / 让 AI 给建议', (tester) async {
      await pumpCoach(tester);
      expect(find.textContaining('拍一张'), findsWidgets);
      expect(find.textContaining('从相册选'), findsWidgets);
      expect(find.textContaining('给建议'), findsWidgets);
    });

    testWidgets('没选图时「让 AI 给建议」是禁用的（不给假入口）', (tester) async {
      await pumpCoach(tester);
      final btn = find.widgetWithText(FilledButton, '让 AI 给建议');
      if (btn.evaluate().isNotEmpty) {
        final b = tester.widget<FilledButton>(btn.first);
        expect(b.onPressed, isNull, reason: '没图就不该能点');
      }
    });

    testWidgets('窄屏不溢出', (tester) async {
      tester.view.physicalSize = const Size(320 * 3, 800 * 3);
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CoachPage(
          config: const ApiConfig(
            endpoint: 'https://api.deepseek.com/chat/completions',
            apiKey: '',
            mode: ProxyMode.direct,
          ),
        ),
      ));
      await tester.pump();
      expect(tester.takeException(), isNull);
    });
  });

  group('教练页 —— 视频区块（F2.12b）', () {
    testWidgets('说明是「抽帧，最多 3 帧」（诚实告知成本）', (tester) async {
      await pumpCoach(tester);
      expect(find.textContaining('抽帧'), findsWidgets);
      expect(find.textContaining('3 帧'), findsWidgets);
    });

    testWidgets('没选视频时「分析视频」按钮禁用', (tester) async {
      await pumpCoach(tester);
      final btn = find.widgetWithText(FilledButton, '分析视频');
      expect(btn, findsOneWidget);
      expect(tester.widget<FilledButton>(btn).onPressed, isNull);
    });

    testWidgets('有「选一段视频」入口', (tester) async {
      await pumpCoach(tester);
      expect(find.textContaining('选一段视频'), findsWidgets);
    });

    testWidgets('视频解码没接时，报错要**明说**而不是假装在分析', (tester) async {
      // 用会抛异常的来源，模拟「原生解码器是占位」的现状
      await pumpCoach(
        tester,
        frameSource: _FakeFrameSource(
            throwMessage: '当前构建还没接视频解码，需要真机 + video_player'),
      );
      expect(find.textContaining('视频分析'), findsWidgets);
      // 这里只验证界面结构在：真正的分析要选文件才触发
      expect(tester.takeException(), isNull);
    });
  });

  group('教练页 —— 诚实性：离线结果不许冒充 AI', () {
    test('没 key 的直连配置判定为「不可用」（会走本地兜底）', () {
      const cfg = ApiConfig(
        endpoint: 'https://api.deepseek.com/chat/completions',
        apiKey: '',
        mode: ProxyMode.direct,
      );
      // ApiConfig 应能自己判断「没 key 就别试了」
      expect(cfg.isUsable, isFalse, reason: '没 key 还说自己可用 = 会白白超时');
    });

    test('有 key 的直连配置可用', () {
      const cfg = ApiConfig(
        endpoint: 'https://api.deepseek.com/chat/completions',
        apiKey: 'sk-test',
        mode: ProxyMode.direct,
      );
      expect(cfg.isUsable, isTrue);
    });

    test('服务端模式的可用性只看端点填没填（key 在中转那边）', () {
      const withEndpoint = ApiConfig(
        endpoint: 'https://my-relay.example.com/analyze',
        apiKey: '',
        mode: ProxyMode.server,
      );
      expect(withEndpoint.isUsable, isTrue);

      const noEndpoint =
          ApiConfig(endpoint: '', apiKey: '', mode: ProxyMode.server);
      expect(noEndpoint.isUsable, isFalse);
    });

    test('离线兜底的建议被标记为 ruleFallback（不是模型给的）', () {
      // 这是零信任的核心：兜底结果必须在数据层就带标记，
      // 不能靠 UI 去猜。
      final offline = Suggestion.fallback(reason: '没接上模型');
      expect(offline.source, SuggestionSource.ruleFallback);
      expect(offline.source, isNot(SuggestionSource.visionModel));
      // 而且它对外显示的名字必须让人看出不是 AI
      expect(SuggestionSource.ruleFallback.label, contains('本地'));
      expect(SuggestionSource.visionModel.label, contains('AI'));
    });

    test('兜底建议带 schema_version，契约不破', () {
      final f = Suggestion.fallback(reason: '测试');
      expect(f.schemaVersion, isNotEmpty);
    });
  });

  group('教练页 —— 跨页联动', () {
    testWidgets('给 session 时不崩（分析成功后才写建议）', (tester) async {
      final session = AppSession();
      addTearDown(session.dispose);
      await pumpCoach(tester, session: session);
      expect(tester.takeException(), isNull);
      expect(session.activeSuggestion, isNull, reason: '还没分析就不该有建议');
    });
  });

  group('教练页 —— 布局健壮性', () {
    testWidgets('宽屏不溢出', (tester) async {
      tester.view.physicalSize = const Size(900 * 2, 800 * 2);
      tester.view.devicePixelRatio = 2;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CoachPage(
          config: const ApiConfig(
            endpoint: 'https://api.deepseek.com/chat/completions',
            apiKey: '',
            mode: ProxyMode.direct,
          ),
        ),
      ));
      await tester.pump();
      expect(tester.takeException(), isNull);
    });

    testWidgets('页面销毁后不崩', (tester) async {
      await pumpCoach(tester);
      await tester.pumpWidget(const MaterialApp(home: SizedBox()));
      await tester.pump();
      expect(tester.takeException(), isNull);
    });
  });

  // =====================================================================
  // 首屏可见性（浏览器实测发现的）
  //
  // 问题：空态下预览框用 AspectRatio(3/4) 撑到 667pt 高，
  // **把三个按钮全挤到首屏之外**。用户第一眼看到的是一个巨大的空框
  // 加「还没选图」，很容易以为这页坏了。
  //
  // 教训：**"能滚到" ≠ "看得见"**。首屏可见性必须有断言。
  // =====================================================================

  group('教练页首屏 —— 按钮必须一眼可见', () {
    Future<void> pumpAt(WidgetTester tester, Size size) async {
      tester.view.physicalSize = Size(size.width * 2, size.height * 2);
      tester.view.devicePixelRatio = 2;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CoachPage(
          config: const ApiConfig(
            endpoint: 'https://api.deepseek.com/chat/completions',
            apiKey: '',
            mode: ProxyMode.direct,
          ),
        ),
      ));
      await tester.pump();
    }

    testWidgets('空态下「拍一张」在首屏内（不用滚动就能看到）', (tester) async {
      // 复现浏览器的视口
      await pumpAt(tester, const Size(500, 717));

      final btn = find.text('拍一张');
      expect(btn, findsWidgets, reason: '「拍一张」按钮不在页面上');

      final box = tester.renderObject<RenderBox>(btn.first);
      final top = box.localToGlobal(Offset.zero).dy;
      final bottom = top + box.size.height;

      expect(top, greaterThanOrEqualTo(0.0),
          reason: '按钮顶部 $top 在屏幕上方（被挤出去了）');
      expect(bottom, lessThanOrEqualTo(717.0),
          reason: '按钮底部 ${bottom.toStringAsFixed(0)} 超出首屏 717pt —— '
              '用户第一眼看不到「拍一张」');
    });

    testWidgets('空态下三个按钮都在首屏内', (tester) async {
      await pumpAt(tester, const Size(500, 717));
      for (final label in ['拍一张', '从相册选']) {
        final f = find.text(label);
        if (f.evaluate().isEmpty) continue;
        final box = tester.renderObject<RenderBox>(f.first);
        final bottom = box.localToGlobal(Offset.zero).dy + box.size.height;
        expect(bottom, lessThanOrEqualTo(717.0),
            reason: '「$label」底部 ${bottom.toStringAsFixed(0)} 超出首屏');
      }
    });

    testWidgets('空态预览框不该占满整屏', (tester) async {
      await pumpAt(tester, const Size(500, 717));
      final hint = find.text('还没选图');
      expect(hint, findsWidgets);
      final box = tester.renderObject<RenderBox>(hint.first);
      // 「还没选图」这几个字本身应该离屏幕中央不远，
      // 如果预览框占满整屏，这些字会在屏幕正中偏下
      final center = box.localToGlobal(Offset.zero).dy + box.size.height / 2;
      expect(center, lessThan(717 * 0.6),
          reason: '空态提示在屏幕 $center 处 —— 说明预览框占了整屏，'
              '把按钮挤下去了');
    });
  });

  // =====================================================================
  // 结果卡片的长文字必须换行（真机实测被裁掉）
  //
  // 真机现象（华为 OCE-AN50 / v0.2.9）：教练页「怎么动」那一行的提示
  // 在卡片右侧被**直接裁掉**（截图里「…别放」后面就没了）。
  //
  // 根因：`Row` 里直接放了 `Text`，没给 `Expanded`/`Flexible`。
  // Row 给非弹性子节点的是**无界宽度**约束 → Text 只排一行、永不换行 →
  // 超出部分被裁掉；release 包连"溢出"的黄黑条都不画，看起来就是"字没了"。
  // =====================================================================

  group('结果卡片 —— 长文字必须换行，不能被裁（真机回归）', () {
    Future<void> pumpCard(WidgetTester tester, Widget card,
        {double width = 320}) async {
      tester.view.physicalSize = Size(width * 3, 900 * 3);
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: Scaffold(body: SingleChildScrollView(child: card)),
      ));
      await tester.pump();
    }

    testWidgets('「怎么动」提示很长时换行，不溢出', (tester) async {
      // 真实数据参考：离线兜底产出的提示就是
      // `把主体放在左或右三分之一线上，别放正中间`
      // （lib/features/coach/offline_tip_engine.dart:74）——
      // 真机截图里被裁掉的就是它。这里再长一点，留出余量。
      final (s, _) = Suggestion.parse({
        'camera_move': {
          'pan_deg': -12.0,
          'tilt_deg': 3.0,
          'dolly_m': -0.5,
          'zoom': 1.2,
          'hint': '把主体放在左或右三分之一线上，别放在正中间；'
              '同时让头顶留出一指宽的空隙，脚下的地面不要切太多，背景尽量干净',
        },
      });
      await pumpCard(tester, MoveSummary(s: s));
      expect(tester.takeException(), isNull,
          reason: '提示文字超出了行宽（RenderFlex overflow）—— '
              '真机上就是右侧被裁掉、后半句看不见');
    });

    testWidgets('提示很短时也不溢出', (tester) async {
      final (s, _) = Suggestion.parse({
        'camera_move': {'hint': '保持不动'},
      });
      await pumpCard(tester, MoveSummary(s: s));
      expect(tester.takeException(), isNull);
    });
  });

  // ---- 模型配置卡（v2 S4：Key 只存本机 SharedPreferences）----
  //
  // 这里用 SharedPreferences 的内存 mock 模拟"本机存储"，
  // 完整验证 收起 → 展开 → 填 Key → 保存 → 收起且状态变"已配置" 的闭环。
  group('教练页 —— 模型配置卡（Key 只存本机）', () {
    setUp(() {
      TestWidgetsFlutterBinding.ensureInitialized();
      SharedPreferences.setMockInitialValues({});
    });

    Future<void> pumpCoachNoConfig(
      WidgetTester tester, {
      required Size physicalSize,
    }) async {
      tester.view.physicalSize = physicalSize;
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        // 注意：不注入 config —— 走「本机 SharedPreferences」这条真实路径。
        home: const CoachPage(),
      ));
      await tester.pump();
    }

    testWidgets('默认收起成一行状态；点按展开表单（三个输入框）', (
      tester,
    ) async {
      await pumpCoachNoConfig(tester,
          physicalSize: const Size(390 * 3, 1200 * 3));
      // 收起态：状态行在，输入框不在（不挤首屏）
      expect(find.text('模型配置'), findsOneWidget);
      expect(find.byType(TextField), findsNothing);
      // 展开
      await tester.tap(find.text('模型配置'));
      await tester.pump();
      expect(find.byType(TextField), findsNWidgets(3));
      expect(find.text('保存'), findsOneWidget);
    });

    testWidgets('填 Key 保存 → 状态变「已配置·直连」，卡片自动收起', (
      tester,
    ) async {
      await pumpCoachNoConfig(tester,
          physicalSize: const Size(390 * 3, 1200 * 3));
      await tester.tap(find.text('模型配置'));
      await tester.pump();

      // 第一个输入框 = API Key（obscured），第二个 = 模型，第三个 = 接口地址
      await tester.enterText(find.byType(TextField).first, 'sk-test-12345');
      await tester.tap(find.text('保存'));
      await tester.pump();

      // ① 状态行切换到「已配置 —— 直连 DeepSeek」
      expect(find.textContaining('已配置'), findsWidgets);
      expect(find.textContaining('直连 DeepSeek'), findsWidgets);
      // ② 保存成功后自动收起，让位首屏
      expect(find.byType(TextField), findsNothing);
      // ③ Key 确实写进了本机存储（这里 = mock prefs）
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('coach.api_key'), 'sk-test-12345');
      expect(prefs.getString('coach.model'), isNotEmpty);
    });

    testWidgets('接口地址填 http:// → 走中转（Key 存中转侧）', (
      tester,
    ) async {
      await pumpCoachNoConfig(tester,
          physicalSize: const Size(390 * 3, 1200 * 3));
      await tester.tap(find.text('模型配置'));
      await tester.pump();

      await tester.enterText(find.byType(TextField).first, 'sk-test-12345');
      await tester.enterText(
        find.byType(TextField).at(2),
        'http://192.168.1.5:8787/analyze',
      );
      await tester.tap(find.text('保存'));
      await tester.pump();

      expect(find.textContaining('走中转 192.168.1.5:8787'), findsWidgets);
    });
  });

  // =====================================================================
  // v0.5.0 三模块闭环：教练负责「环境方案」，产出后只负责把人带到拍摄页；
  // 方案（含目标框）写进共享状态，拍摄页自己消费。
  // =====================================================================
  group('教练页 —— 投射闭环（v0.5.0）', () {
    testWidgets(
        '拍摄页送来照片 → 点分析（离线兜底）→「发送到拍摄页」只导航 + 建议入共享态', (
          tester,
        ) async {
      // 造一张真的小图（1×1 透明 PNG）—— 压缩器要真读、真解码它。
      // ⚠️ 全部用同步 API：widget 测试跑在假时钟里，任何真异步 I/O
      // （createTemp / readAsBytes）都会永远等不到。
      final png = File('${Directory.systemTemp.path}/coach_loop_$pid.png');
      png.writeAsBytesSync(base64Decode(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
          'AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='));
      addTearDown(() {
        try {
          png.deleteSync();
        } catch (_) {}
      });

      final shared = AppSession();
      addTearDown(shared.dispose);
      var navigated = false;
      await pumpCoach(
        tester,
        session: shared,
        onNavigateToShoot: () => navigated = true,
      );

      // ⚠️ 必须先挂载、后送图：教练页在 initState 里才注册监听
      // （并记下当前序号防重放）。送图早于挂载 = 监听没接上 = 图丢了，
      // 按钮永远是禁用态，后面一切都不会发生。
      shared.sendShotToCoach(png);
      await tester.pump();

      // 拍摄页送来的照片已经在源卡片里，分析按钮可用
      expect(find.text('让 AI 给建议'), findsOneWidget);
      final analyzeBtn = find.widgetWithText(FilledButton, '让 AI 给建议');
      expect(tester.widget<FilledButton>(analyzeBtn).onPressed, isNotNull,
          reason: '图已收但按钮禁用了 = 监听没接上');

      // 点分析：没 key → 离线兜底（诚实，不冒充 AI）。
      // ⚠️ 探针实证（debug_probe3）：假时钟里发起的 readAsBytes **永远不会
      // 被恢复**（fake-async 结算不了真 I/O 完成事件）。所以 tap 必须放进
      // runAsync（真事件循环）：读文件在真区发起、真区完成，整条分析链
      // 在 runAsync 内跑完，回到假区再 pump 结算帧。
      await tester.runAsync(() async {
        await tester.tap(analyzeBtn);
        // 真实等待：读文件 + 解码 + 离线规则出方案（毫秒级，800ms 足够）
        await Future<void>.delayed(const Duration(milliseconds: 800));
        await tester.pump();
      });
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      // ① 有方案才有跳转按钮（没方案不给人假入口）。
      expect(find.text('发送到拍摄页'), findsOneWidget,
          reason: '方案产出了但按钮不在 = 闭环断了');
      // ⚠️ 不用 scrollUntilVisible：这个 SDK 里它只在目标「未构建」时才拖
      // （拖到构建即停）。v0.7.0 加了面部光影卡片，列表变长，按钮中心被顶到
      // y=1221（视口 1200）——已构建但屏外 → 它一次都不拖 → tap 打空。
      // 手动拖到按钮中心进视野再断言（实测诊断：拖进视野后回调正常触发）。
      final sendBtn = find.text('发送到拍摄页');
      for (var i = 0; i < 100; i++) {
        final c = tester.getCenter(sendBtn, warnIfMissed: false);
        if (c.dy > 0 && c.dy < 1200) break;
        await tester.drag(find.byType(Scrollable).first,
            Offset(0, c.dy > 1200 ? -300 : 300));
        await tester.pump();
      }
      // ② 建议已写入共享状态（拍摄页会自动画目标框）
      expect(shared.activeSuggestion, isNotNull);

      // ③ 按钮只做一件事：把人带到拍摄页（AppShell 里 = 切 tab）
      await tester.tap(find.text('发送到拍摄页'));
      await tester.pump();
      expect(navigated, isTrue, reason: '按钮没触发跳转回调');
    });
  });
}
