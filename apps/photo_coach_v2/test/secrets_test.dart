import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/coach/secrets_page.dart';

void main() {
  group('拍照秘诀数据契约', () {
    test('恰好 6 招，标题不重复', () {
      expect(kSecretsTips, hasLength(6));
      final titles = kSecretsTips.map((t) => t.title).toSet();
      expect(titles.length, kSecretsTips.length);
    });

    test('每招 3 句话，没有空句', () {
      for (final t in kSecretsTips) {
        expect(t.points, hasLength(3), reason: '${t.title} 应恰好 3 句');
        for (final p in t.points) {
          expect(p.trim(), isNotEmpty, reason: '${t.title} 有空句');
        }
      }
    });

    test('每招的 SVG 资源文件真实存在（已注册 pubspec assets/secrets/）', () {
      for (final t in kSecretsTips) {
        expect(File(t.svg).existsSync(), isTrue,
            reason: '${t.title} 的示意图缺失: ${t.svg}');
      }
    });

    test('每招的正确/错误示例图都存在且不是空文件', () {
      for (final t in kSecretsTips) {
        for (final path in [t.goodImage, t.badImage]) {
          expect(path, isNotNull, reason: '${t.title} 缺少示例图路径');
          final f = File(path!);
          expect(f.existsSync(), isTrue, reason: '${t.title} 缺失示例图: $path');
          expect(f.lengthSync(), greaterThan(10000),
              reason: '${t.title} 示例图文件过小: $path');
        }
      }
    });
  });

  group('拍照秘诀 UI 冒烟', () {
    testWidgets('教练 tab 入口 → 点进列表页 → 6 招全在', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: SecretsEntryCard())),
      );
      await tester.tap(find.text('拍照秘诀'));
      await tester.pumpAndSettle();
      expect(find.text('拍照秘诀'), findsWidgets); // 页标题 + 入口文案
      // 测试视口小，ListView 懒加载：先验可见的前 4 招
      for (var i = 0; i < 4; i++) {
        expect(find.text('招 ${i + 1} · ${kSecretsTips[i].title}'), findsOneWidget);
      }
      // 滚到底，再验后 2 招
      await tester.drag(find.byType(ListView), const Offset(0, -1500));
      await tester.pumpAndSettle();
      for (var i = 4; i < 6; i++) {
        expect(find.text('招 ${i + 1} · ${kSecretsTips[i].title}'), findsOneWidget);
      }
    });
  });
}
