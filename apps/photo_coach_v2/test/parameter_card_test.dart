import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/params/exposure_knowledge.dart';
import 'package:photo_coach_v2/features/params/parameter_advisor.dart';
import 'package:photo_coach_v2/features/params/parameter_card.dart';
import 'package:photo_coach_v2/features/params/shot_exif.dart';

/// 「建议参数」卡的测试。
///
/// 人类反馈过一次「太复杂」——所以这个文件同时守**简单**：
/// 卡片上只许有两行（建议值 + 一句提醒），依据必须收在 ⓘ 里，
/// 默认**不许**把出处、EV100、实测数据摊在用户面前。
/// 另外守诚实：没有出处时，界面上不许出现任何建议数字。
void main() {
  Future<void> pump(WidgetTester tester, Widget child) async {
    tester.view.physicalSize = const Size(390 * 3, 900 * 3);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(
      theme: ThemeData.dark(),
      home: Scaffold(body: SingleChildScrollView(child: child)),
    ));
    await tester.pump();
  }

  // 暗光实测（ISO 3200 / 1/30 / f1.8）→ 流水 2s 时 ISO 才算得出来
  ParameterAdvice waterAdvice() => adviseParameters(
        intent: ShootingIntent.water,
        shot: const ShotExif(iso: 3200, shutterSeconds: 1 / 30, aperture: 1.8),
      );

  testWidgets('默认只显示两行：建议值 + 本机能设的', (tester) async {
    await pump(tester,
        ParameterCard(advice: waterAdvice(), appCanSet: const ['曝光补偿 -0.7 EV']));

    expect(find.textContaining('ISO 64'), findsOneWidget);
    expect(find.textContaining('快门 2s'), findsOneWidget);
    expect(find.textContaining('本机能设'), findsOneWidget);

    // 关键：默认看不到依据/出处/计算过程（"太复杂"的根因）
    expect(find.textContaining('canon.com.hk'), findsNothing);
    expect(find.textContaining('EV100'), findsNothing);
    expect(find.textContaining('照片实测'), findsNothing);
  });

  testWidgets('点 ⓘ 才展开依据与出处（想核对的人点一下就有）', (tester) async {
    await pump(tester, ParameterCard(advice: waterAdvice()));

    expect(find.textContaining('canon.com.hk'), findsNothing);
    await tester.tap(find.byTooltip('依据'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.textContaining('canon.com.hk'), findsWidgets,
        reason: '出处要能核对（可复制）');
    expect(find.textContaining('EV100'), findsWidgets,
        reason: '计算依据也要能看到');
    expect(tester.takeException(), isNull);
  });

  testWidgets('没有出处的意图：明说给不出，且界面上没有任何建议数字', (tester) async {
    await pump(
        tester, ParameterCard(advice: adviseParameters(intent: ShootingIntent.portrait)));

    expect(find.text('给不出建议'), findsOneWidget);
    expect(find.textContaining('ISO'), findsNothing,
        reason: '没有出处的意图，界面上不许出现 ISO 建议值');
    expect(find.textContaining('1/'), findsNothing,
        reason: '不许出现快门建议值');
  });

  testWidgets('晴天长曝：不给错的 ISO，只提醒一句「必须加 ND」', (tester) async {
    final advice = adviseParameters(
      intent: ShootingIntent.water,
      shot: const ShotExif(iso: 50, shutterSeconds: 1 / 2000, aperture: 1.8),
    );
    await pump(tester, ParameterCard(advice: advice));

    expect(find.textContaining('快门 2s'), findsOneWidget);
    expect(find.textContaining('ISO'), findsNothing,
        reason: '算出来低于任何相机最低 ISO 时不许给数字（会给出一片死白）');
    expect(find.textContaining('ND'), findsOneWidget);
  });

  testWidgets('意图选择器：一行放下五个，点了会回调', (tester) async {
    ShootingIntent? picked;
    await pump(
      tester,
      IntentPicker(
        value: ShootingIntent.portrait,
        onChanged: (v) => picked = v,
      ),
    );

    for (final i in ShootingIntent.values) {
      expect(find.text(i.label), findsOneWidget);
    }
    await tester.tap(find.text('流水'));
    expect(picked, ShootingIntent.water);
  });
}
