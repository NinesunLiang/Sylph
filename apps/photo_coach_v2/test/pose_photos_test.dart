import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/poses/pose.dart';

/// 真实参考照姿势库（性別 → 姿态 两级分类）的回归测试。
///
/// 这些断言锁的是**数据契约**：图必须在、指导必须齐、分类必须自洽。
/// 素材缺失或字段漏填时，这里先红，而不是等到真机上一片空白。
void main() {
  group('参考照库 —— 数据契约', () {
    test('有内容，且 id 唯一', () {
      expect(photoPoses, isNotEmpty);
      final ids = photoPoses.map((p) => p.id).toSet();
      expect(ids.length, photoPoses.length, reason: 'id 必须唯一');
    });

    test('每张都有图、有指导、有标题', () {
      for (final p in photoPoses) {
        expect(p.hasPhoto, isTrue, reason: '${p.id} 没有 imagePath');
        expect(p.imagePath, startsWith('assets/poses/'),
            reason: '${p.id} 的图不在 assets/poses/ 下');
        expect(p.guidance, isNotNull, reason: '${p.id} 缺指导数据');
        expect(p.title.trim(), isNotEmpty, reason: '${p.id} 缺标题');
      }
    });

    test('指导字段没有空值（翻面后不能有空白行）', () {
      for (final p in photoPoses) {
        final g = p.guidance!;
        expect(g.cameraHeight.trim(), isNotEmpty, reason: '${p.id} 缺机位');
        expect(g.direction.trim(), isNotEmpty, reason: '${p.id} 缺方向');
        expect(g.framing.trim(), isNotEmpty, reason: '${p.id} 缺景别');
        expect(g.action.trim(), isNotEmpty, reason: '${p.id} 缺动作');
        expect(g.expression.trim(), isNotEmpty, reason: '${p.id} 缺表情');
        expect(g.why.trim(), isNotEmpty, reason: '${p.id} 缺「为什么好看」');
      }
    });

    test('一级分类只有性別；二级分类是姿态', () {
      expect(PoseCatalog.genders.first, '全部');
      for (final p in photoPoses) {
        expect(['女', '男'], contains(p.gender), reason: '${p.id} 性別非法');
        expect(['站', '坐', '躺'], contains(p.posture), reason: '${p.id} 姿态非法');
      }
    });

    test('女有站/坐/躺，男只有站/坐（男性素材进来之后）', () {
      expect(PoseCatalog.posturesOf('女'), containsAll(['站', '坐', '躺']));
      final male = PoseCatalog.posturesOf('男');
      expect(male, contains('站'), reason: '男应该有站姿');
      expect(male, contains('坐'), reason: '男应该有坐姿');
      expect(male, isNot(contains('躺')), reason: '男按约定不做躺姿');
      for (final p in photoPoses.where((p) => p.gender == '男')) {
        expect(['站', '坐'], contains(p.posture));
      }
    });

    test('男性素材已入库，站姿和坐姿都有（不再是空分类）', () {
      final men = PoseCatalog.photos(gender: '男');
      expect(PoseCatalog.genders, contains('男'));
      expect(men.length, greaterThanOrEqualTo(30),
          reason: '目标是约 30 个男性站/坐姿，实际只有 ${men.length}');
      expect(men.where((p) => p.posture == '站').length, greaterThan(0),
          reason: '男站姿一张都没有');
      expect(men.where((p) => p.posture == '坐').length, greaterThan(0),
          reason: '男坐姿一张都没有');
    });

    test('补充包条目用的是 c_ 前缀（可与原始素材区分）', () {
      final added = photoPoses.where((p) => p.id.startsWith('c_')).toList();
      expect(added.length, greaterThanOrEqualTo(100),
          reason: '补充包应该有上百张，实际 ${added.length}');
      // 原始 140 张的 id 不带 c_ 前缀，两批不能混
      final orig = photoPoses.where((p) => !p.id.startsWith('c_')).toList();
      expect(orig.length, 140, reason: '原始素材应保持 140 张不变');
    });

    test('posturesOf 的第一项是「全部」，且只列该性別真实有的姿态', () {
      for (final g in PoseCatalog.genders) {
        final ps = PoseCatalog.posturesOf(g);
        expect(ps.first, '全部');
        final real = photoPoses
            .where((p) => g == '全部' || p.gender == g)
            .map((p) => p.posture)
            .toSet();
        expect(ps.toSet(), {'全部', ...real},
            reason: '$g 的姿态列表与实际数据不一致');
      }
    });

    test('photos() 两级筛选都对', () {
      expect(PoseCatalog.photos().length, photoPoses.length);
      final women = PoseCatalog.photos(gender: '女');
      expect(women, isNotEmpty);
      expect(women.every((p) => p.gender == '女'), isTrue);

      final sit = PoseCatalog.photos(posture: '坐');
      expect(sit, isNotEmpty);
      expect(sit.every((p) => p.posture == '坐'), isTrue);

      final pair = PoseCatalog.photos(gender: '女', posture: '站');
      expect(pair.every((p) => p.gender == '女' && p.posture == '站'), isTrue);

      expect(PoseCatalog.photos(gender: '男', posture: '躺'), isEmpty,
          reason: '男没有躺姿素材，这里必须是空的');
    });

    test('searchPhotos 能搜到动作 / 表情 / 为什么好看', () {
      expect(PoseCatalog.searchPhotos('').length, photoPoses.length);
      expect(PoseCatalog.searchPhotos('zzz不存在zzz'), isEmpty);

      final probe = photoPoses.first;
      final kw = probe.guidance!.action.substring(0, 2);
      expect(PoseCatalog.searchPhotos(kw), isNotEmpty,
          reason: '按动作关键词「$kw」搜不到东西');
    });

    test('去重：同一动作+表情不留两张（决定性字段不能全同）', () {
      // 这是去重步骤的机器化护栏：如果以后批量灌图又灌进重复动作，
      // 这条会红。注意只比"决定性字段"，衣服/背景/机位不同不算重复。
      final seen = <String, String>{};
      final dups = <String>[];
      for (final p in photoPoses) {
        final g = p.guidance!;
        final key = [p.posture, g.action.trim(), g.expression.trim()].join('|');
        final prev = seen[key];
        if (prev != null) {
          dups.add('$prev 与 ${p.id}');
        } else {
          seen[key] = p.id;
        }
      }
      expect(dups, isEmpty, reason: '发现动作+表情全同的两张：${dups.join("，")}');
    });
  });
}
