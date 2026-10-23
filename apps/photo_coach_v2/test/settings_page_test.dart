import 'package:camera_platform_interface/camera_platform_interface.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/camera/camera_session.dart';
import 'package:photo_coach_v2/features/settings/settings_page.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/fake_camera_platform.dart';

/// 设置页（入口：拍摄页右上角齿轮）的测试。
///
/// **2026-10-11 三模块职责重构**：「拍摄参数」类目已整体删除 ——
/// 出片在系统相机，App 内预览调参数（EV/变焦/闪光）无用。
/// 这一页现在只剩两件事：模型 API Key 配置 + 功能说明。
/// 本文件用一条「不该再有拍摄参数」的回归用例锁死这个决定，
/// 其余用例守护模型 Key 的读取/保存/收起行为。

/// 造一个**已经就绪**的相机会话（部分用例需要）。
///
/// ⚠️ 必须一边 pump 一边等：`testWidgets` 跑在**假时钟**里，而假相机内部有
/// `Future.delayed(1ms)`。直接 `await s.initialize()` 的话没有任何东西推进
/// 假时钟 → 永远等不到 → 整个测试文件死等（实测卡满 10 分钟被系统杀掉）。
/// 正确做法：先发起、pump 推进、再 await。
Future<CameraSession> readySession(WidgetTester tester) async {
  CameraPlatform.instance = FakeCameraPlatform(
    cameras: [
      const CameraDescription(
          name: 'back',
          lensDirection: CameraLensDirection.back,
          sensorOrientation: 90)
    ],
  );
  final s = CameraSession();
  final init = s.initialize();
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
  await init;
  return s;
}

Future<void> pumpSettings(WidgetTester tester) async {
  tester.view.physicalSize = const Size(390 * 3, 900 * 3);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      theme: ThemeData.dark(),
      home: const SettingsPage(),
    ),
  );
  await tester.pump();
}

void main() {
  group('设置页 —— 拍摄参数类目已删除（三模块重构回归）', () {
    testWidgets('没有「拍摄参数」入口（出片在系统相机，调参没用）',
        (tester) async {
      final s = await readySession(tester);
      addTearDown(s.dispose);
      await pumpSettings(tester);

      expect(find.text('拍摄参数'), findsNothing,
          reason: '拍摄参数不该再是设置里的类目');
      expect(find.byType(Slider), findsNothing, reason: '连滑块都不该出现');
      expect(tester.takeException(), isNull);
    });

    testWidgets('说明区如实写清：照片存相册、AI 需联网、ISO 做不到',
        (tester) async {
      final s = await readySession(tester);
      addTearDown(s.dispose);
      await pumpSettings(tester);

      expect(find.textContaining('系统相册'), findsWidgets);
      expect(find.textContaining('DeepSeek'), findsWidgets);
      expect(find.textContaining('本地规则'), findsWidgets,
          reason: '要说清连不上时会退化成规则兜底，不能让人以为一定是 AI 给的');
      expect(find.textContaining('教练页里也有同一处'), findsWidgets,
          reason: 'v0.4.0 起 Key 在设置页也能填，说明不能只指路到教练页');
    });
  });

  group('设置页 —— 模型 API Key（v0.4.0 反馈：要能在设置里填）', () {
    testWidgets('没配过：有「模型配置」卡，状态说未配置，表单直接展开',
        (tester) async {
      SharedPreferences.setMockInitialValues({});
      final s = await readySession(tester);
      addTearDown(s.dispose);
      await pumpSettings(tester);
      await tester.pump(const Duration(milliseconds: 30));

      expect(find.text('模型配置'), findsOneWidget);
      // 展开时状态文本出现两次（标题行 + 表单底栏），各出现一次即可。
      expect(find.textContaining('未配置'), findsWidgets);
      // 用户就是来配置的 → 表单一进来就展开（教练页那份则默认收起）。
      expect(find.text('API Key'), findsOneWidget);
      expect(find.text('deepseek-v4-flash'), findsOneWidget,
          reason: '模型输入框预填默认值，省得手打');
      expect(tester.takeException(), isNull);
    });

    testWidgets('填 Key → 保存 → 状态变「已配置」，并真的写进 SharedPreferences',
        (tester) async {
      SharedPreferences.setMockInitialValues({});
      final s = await readySession(tester);
      addTearDown(s.dispose);
      await pumpSettings(tester);
      await tester.pump(const Duration(milliseconds: 30));

      await tester.enterText(find.byType(TextField).first, 'sk-test-12345');
      await tester.tap(find.text('保存'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 30));

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('coach.api_key'), 'sk-test-12345',
          reason: '保存要落到本机存储（Key 只存手机，这个断言守住存储路径）');

      expect(find.textContaining('已配置'), findsOneWidget,
          reason: '保存后状态必须从「未配置」切到「已配置」，用户才知道成了');
      expect(find.textContaining('Key 存本机'), findsOneWidget);
      expect(find.text('API Key'), findsNothing,
          reason: '保存成功后表单收起，Key 字段不再回显（v0.3.0 纪律）');
      expect(tester.takeException(), isNull);
    });

    testWidgets('之前存过 Key（和自定义模型）：读回，状态「已配置」，表单收起',
        (tester) async {
      SharedPreferences.setMockInitialValues({
        'coach.api_key': 'sk-preset-000',
        'coach.model': 'deepseek-v4-pro',
        'coach.endpoint': 'https://api.deepseek.com/chat/completions',
      });
      final s = await readySession(tester);
      addTearDown(s.dispose);
      await pumpSettings(tester);
      await tester.pump(const Duration(milliseconds: 30));

      expect(find.textContaining('已配置'), findsOneWidget);
      expect(find.textContaining('Key 存本机'), findsOneWidget);
      expect(find.textContaining('deepseek-v4-pro'), findsWidgets,
          reason: '状态行要如实显示存的是哪个模型');
      expect(find.text('API Key'), findsNothing,
          reason: '已经配好的用户不需要再看到表单（保存成功即收起）');
      expect(tester.takeException(), isNull);
    });

    testWidgets('配了局域网中转（http://）：状态显示「走中转」+ host:port',
        (tester) async {
      SharedPreferences.setMockInitialValues({
        'coach.api_key': 'sk-relay-1',
        'coach.endpoint': 'http://192.168.1.10:8787/chat/completions',
      });
      final s = await readySession(tester);
      addTearDown(s.dispose);
      await pumpSettings(tester);
      await tester.pump(const Duration(milliseconds: 30));

      expect(find.textContaining('中转'), findsOneWidget);
      expect(find.textContaining('192.168.1.10:8787'), findsOneWidget,
          reason: '中转常用非常规端口，只写 host 会误导用户');
      expect(find.textContaining('Key 存中转侧'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
