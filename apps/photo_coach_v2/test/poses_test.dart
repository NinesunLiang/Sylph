import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/poses/pose.dart';

/// 姿势库测试（v0.4.0 重写）。
///
/// 这版之前测的是火柴人库（`PoseCatalog.builtIn`，31 个代码绘制姿势）。
/// v0.4.0 按用户要求删掉了火柴人库（`builtIn = []`），App 内姿势库
/// 只剩 **真实参考照片**（顶层 const [photoPoses]，250 张，
/// 由 .work/poses/gen_dart.py 生成）。所以这些测试现在断言的是：
///   · 参考照库的数据完整性（250 张、id 唯一、字段齐全、全是真照片）
///   · 性別/姿态两级分类的完整性
///   · 筛选与搜索的行为
///   · 火柴人库「已删但接口保留」的契约（builtIn 恒为空，方法不崩）
void main() {
  group('参考照片姿势库（photoPoses）', () {
    test('不少于 30 张（F3.2 目标），且 id 唯一', () {
      expect(photoPoses.length, greaterThanOrEqualTo(30),
          reason: '参考照片库缩水了？');
      final ids = photoPoses.map((p) => p.id).toSet();
      expect(ids.length, photoPoses.length, reason: 'id 必须唯一');
    });

    test('每张参考照：标题/分类/场景/标签/要点齐全，且真的是照片（不是火柴人）', () {
      for (final p in photoPoses) {
        expect(p.title.trim(), isNotEmpty, reason: '${p.id} 缺标题');
        expect(p.category.trim(), isNotEmpty, reason: '${p.id} 缺分类');
        expect(p.scene.trim(), isNotEmpty, reason: '${p.id} 缺场景');
        expect(p.tags, isNotEmpty, reason: '${p.id} 缺标签');
        expect(p.tips, isNotEmpty, reason: '${p.id} 缺拍摄要点');
        expect(p.guidance, isNotNull, reason: '${p.id} 缺翻面指导');
        expect(p.hasPhoto, isTrue,
            reason: '${p.id} 声称是参考照却没有 imagePath');
        expect(p.strokes, isEmpty,
            reason: '${p.id} 是参考照，不该有火柴人线条');
      }
    });

    test('每张参考照的性别/姿态都非空，姿态取值合法（站/坐/躺）', () {
      const validPostures = {'站', '坐', '躺'};
      for (final p in photoPoses) {
        expect(p.gender, isNotEmpty, reason: '${p.id} 缺性别');
        expect(p.posture, isNotEmpty, reason: '${p.id} 缺姿态');
        expect(validPostures, contains(p.posture),
            reason: '${p.id} 的姿态「${p.posture}」不合法');
      }
    });

    test('性別一级分类：「全部」开头，男女都有内容', () {
      final genders = PoseCatalog.genders;
      expect(genders.first, '全部');
      expect(genders, containsAll(['女', '男']));
      expect(PoseCatalog.photos(gender: '女'), isNotEmpty);
      expect(PoseCatalog.photos(gender: '男'), isNotEmpty);
    });

    test('姿态二级分类随性別联动：女有躺，男没有躺就不该出现', () {
      final female = PoseCatalog.posturesOf('女');
      final male = PoseCatalog.posturesOf('男');
      expect(female.first, '全部');
      expect(female, containsAll(['站', '坐', '躺']));
      expect(male, containsAll(['站', '坐']));
      // 素材里没有男性躺姿 → 不该出现
      expect(male, isNot(contains('躺')));
    });

    test('photos 按性別 + 姿态两级筛选，乱传值返回空而不是全量', () {
      final female = PoseCatalog.photos(gender: '女');
      expect(female.every((p) => p.gender == '女'), isTrue);

      final sitting = PoseCatalog.photos(posture: '坐');
      expect(sitting.every((p) => p.posture == '坐'), isTrue);

      final combo = PoseCatalog.photos(gender: '男', posture: '坐');
      expect(combo, isNotEmpty);
      expect(combo.every((p) => p.gender == '男' && p.posture == '坐'), isTrue);

      expect(PoseCatalog.photos(gender: '不存在'), isEmpty);
      expect(PoseCatalog.photos(posture: '不存在'), isEmpty);
    });

    test('searchPhotos：空关键词返回全量，命中标题/标签/翻面指导，瞎搜返回空', () {
      expect(PoseCatalog.searchPhotos('').length, photoPoses.length);
      expect(PoseCatalog.searchPhotos('   ').length, photoPoses.length);

      // 标题命中
      expect(PoseCatalog.searchPhotos('倚靠').first.id,
          'f_stand_lean_car_bent_leg');
      // 标签命中
      expect(PoseCatalog.searchPhotos('lean_car_bent_leg'), isNotEmpty);
      // 翻面指导文案命中（四分之三侧 是 guidance.direction）
      expect(
          PoseCatalog.searchPhotos('四分之三侧')
              .any((p) => p.id == 'f_stand_lean_car_bent_leg'),
          isTrue);
      // 瞎搜
      expect(PoseCatalog.searchPhotos('zzz不存在zzz'), isEmpty);
    });
  });

  group('火柴人库（v0.4.0 已删，接口保留）', () {
    test('builtIn 是空列表 —— 库删了，但调用面不能崩', () {
      expect(PoseCatalog.builtIn, isEmpty);
      expect(PoseCatalog.categories, ['全部']);
      expect(PoseCatalog.byCategory('站姿'), isEmpty);
      expect(PoseCatalog.byCategory('不存在'), isEmpty);
      expect(PoseCatalog.search(''), isEmpty);
      expect(PoseCatalog.search('跳跃'), isEmpty);
    });
  });
}
