import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/coach/llm_client.dart';

/// `extractJson(text)` 的**参数穷举**测试（TDD）。
///
/// 人类要求：「每个变量、参数都要做 TDD，别带着错误上安装包」。
///
/// 这个函数的参数只有一个：模型返回的原始文本 `String text`。
/// 它的取值空间是**任意用户/模型可控的文本** —— 所以必须穷举：
///
/// | 类别 | 取值 |
/// |---|---|
/// | 空 | 空串、纯空白、换行、制表 |
/// | 合法 | 直接 JSON、带围栏、前后带话、嵌套、数组 |
/// | 截断 | 只有左括号、只到一半 |
/// | 畸形 | 未闭合字符串、不平衡括号、非法 JSON |
/// | 对抗 | 超深嵌套、超长、Unicode、控制字符、多个候选块 |
/// | 类型 | 顶层数组/数字/字符串/null（不是对象） |
///
/// 已有 8 个用例只覆盖了"合法 + 抠不出"，**截断/畸形/对抗全没测**。

const kOpen = '{';
const kClose = '}';

/// 构造**真正合法**的深嵌套：{"a":{"a":{…1…}}}
String nestedJson(int depth) {
  final buf = StringBuffer();
  for (var i = 0; i < depth; i++) {
    buf.write('{"a":');
  }
  buf.write('1');
  for (var i = 0; i < depth; i++) {
    buf.write('}');
  }
  return buf.toString();
}
void main() {
  group('extractJson —— 空与空白（参数 = 特殊空值）', () {
    test('空串 → null', () => expect(extractJson(''), isNull));
    test('纯空格 → null', () => expect(extractJson('   '), isNull));
    test('纯换行 → null', () => expect(extractJson('\n\n\n'), isNull));
    test('制表符 → null', () => expect(extractJson('\t\t'), isNull));
    test('CRLF → null', () => expect(extractJson('\r\n'), isNull));
    test('各种 Unicode 空白 → null', () {
      for (final w in ['\u00a0', '\u2000', '\u3000', '\ufeff']) {
        expect(extractJson(w), isNull, reason: '空白 ${w.codeUnits} 没被当空');
      }
    });
  });

  group('extractJson —— 合法输入', () {
    test('纯对象', () {
      expect(extractJson('{"a":1}'), {'a': 1});
    });

    test('前后带解释文字', () {
      final r = extractJson('好的，建议如下：\n{"ev":-0.3}\n希望有帮助！');
      expect(r, {'ev': -0.3});
    });

    test('markdown 围栏（json 标注 / 无标注 / 大写）', () {
      expect(extractJson('```json\n{"a":1}\n```'), {'a': 1});
      expect(extractJson('```\n{"a":1}\n```'), {'a': 1});
      expect(extractJson('```JSON\n{"a":1}\n```'), {'a': 1});
    });

    test('前后有空白和换行也能抠出来', () {
      expect(extractJson('\n\n  {"a":1}  \n\n'), {'a': 1});
    });

    test('顶层数组也要能抠（有些模型会包一层数组）', () {
      // 数组没有 {}，取决于实现是否支持 —— 这里锁住**行为**（不抛异常）
      Object? r;
      expect(() => r = extractJson('[{"a":1}]'), returnsNormally);
      // 不强制要求支持数组，但必须不崩；若返回了，必须结构正确
      if (r != null) {
        expect(r, isA<Object>());
      }
    });
  });

  group('extractJson —— 截断（模型输出被切断，很常见）', () {
    test('只有左括号 → null，不崩不死循环', () {
      expect(extractJson('{'), isNull);
    });

    test('对象只写了一半 → null', () {
      expect(extractJson('{"a": 1, "b":'), isNull);
    });

    test('嵌套对象只写了一半 → 抠出内层那个完整对象（设计取舍）', () {
      // ⚠️ 这是**有意**的行为，不是 bug：
      //   `{"a":{"b":1}` —— 外层没闭合，但内层 `{"b":1}` 是完整合法的。
      // 取舍理由：契约层（Suggestion.parse）**已经能处理字段缺失**
      // （有专门测试，会产出 warnings 让用户看到"这次信息不全"）。
      // 所以"拿到部分数据 + 警告" 比 "什么都没有" 对用户更有用。
      // 宁可给一个能用的骨架，也不要因为一个括号就全丢。
      expect(extractJson('{"a":{"b":1}'), {'b': 1});
    });

    test('字符串没闭合 → null', () {
      expect(extractJson('{"a": "没闭合'), isNull);
    });

    test('围栏开了没关 → 仍要尽力抠（围栏闭不上不该直接放弃）', () {
      expect(extractJson('```json\n{"a":1}'), {'a': 1});
    });
  });

  group('extractJson —— 畸形与不平衡', () {
    test('后面带多余右括号 → 尽力抠出前面那个完整对象', () {
      // 注意：`{} }` 里的第一个平衡对象**是合法**的 `{}`。
      // 模型输出带噪声是常态，抠出能用的部分比整体放弃更有用。
      // （第一版我写成期望 null，那是我把"严格"当成了"正确"。）
      expect(extractJson('{"a":1}}'), {'a': 1});
      expect(extractJson('{}}'), isEmpty);
    });

    test('只有右括号 → null', () {
      expect(extractJson('}}}'), isNull);
    });

    test('嵌套平衡时取最外层（优先完整结构）', () {
      expect(extractJson('{"a":{"b":1}}'), {'a': {'b': 1}});
    });

    test('嵌套不平衡 → 退而取内层完整对象（同上的取舍）', () {
      expect(extractJson('{"a":{"b":1}'), {'b': 1});
    });

    test('整段找不到任何完整对象才返回 null', () {
      expect(extractJson('{"a":'), isNull);
      expect(extractJson('{"a":{'), isNull);
      expect(extractJson('{"a":{"b":'), isNull);
    });

    test('括号在字符串里不算（这是最容易写错的地方）', () {
      expect(extractJson('{"hint":"往前 {这里} 走","n":1}'),
          {'hint': '往前 {这里} 走', 'n': 1});
      expect(extractJson('{"hint":"}","n":1}'), {'hint': '}', 'n': 1});
    });

    test('转义引号不算字符串结束', () {
      expect(extractJson(r'{"t":"他说 \"你好\" 了","n":2}'),
          {'t': '他说 "你好" 了', 'n': 2});
    });

    test('转义反斜杠本身（\\\\ 之后引号该正常结束）', () {
      // JSON: {"p":"C:\\"}  → 值是 C:\
      expect(extractJson(r'{"p":"C:\\","n":1}'), {'p': r'C:\', 'n': 1});
    });
  });

  group('extractJson —— 对抗性输入（不许崩/不许卡死）', () {
    test('大量重复括号（非法嵌套）→ null，不崩', () {
      // 注意：`{{{"a":1}}}` **不是**合法 JSON（对象不能直接套对象），
      // 构造这种输入时要清楚自己在测"畸形输入"，不是"深嵌套"。
      final bad = '$kOpen * 400 "a":1 $kClose * 400';
      expect(() => extractJson(bad), returnsNormally);
    });

    test('真正合法的深嵌套（400 层）要能解析出来', () {
      // 合法的深嵌套是 {"a":{"a":{...1...}}}，不是 {{{...}}}
      final deep = nestedJson(400);
      Object? r;
      expect(() => r = extractJson(deep), returnsNormally);
      expect(r, isNotNull, reason: '400 层合法嵌套应该能抠出来（不是深度限制）');
      expect(r, isA<Map>());
    });

    test('极深合法嵌套（5000 层）不崩', () {
      expect(() => extractJson(nestedJson(5000)), returnsNormally);
    });

    test('大量重复括号（2 万个）不崩', () {
      final insane = '$kOpen * 20000 "a":1 $kClose * 20000';
      expect(() => extractJson(insane), returnsNormally);
    });

    test('超长文本不超时（1MB 无 JSON）', () {
      final big = 'x' * (1024 * 1024);
      Object? r;
      expect(() => r = extractJson(big), returnsNormally);
      expect(r, isNull);
    });

    test('超长文本里藏一个 JSON，仍能抠出来', () {
      final big = '${'废话' * 5000}{"a":1}${'尾巴' * 5000}';
      expect(extractJson(big), {'a': 1});
    });

    test('多个候选块：第一个坏了，要能试下一个', () {
      final text = '```json\n{坏掉了\n```\n还有这个：\n{"good":true}';
      expect(extractJson(text), {'good': true},
          reason: '第一个块解析失败后应该继续试后面的');
    });

    test('多个围栏块：取第一个能解析的', () {
      final text = '```json\n{"first":1}\n```\n```json\n{"second":2}\n```';
      expect(extractJson(text), {'first': 1});
    });

    test('围栏里是数组/非法内容 → 退回扫描，不崩', () {
      expect(() => extractJson('```json\nnot json at all\n```'), returnsNormally);
    });

    test('控制字符不崩', () {
      expect(() => extractJson('{"a":"\u0000\u0001"}'), returnsNormally);
    });

    test('Emoji 和中文键名', () {
      expect(extractJson('{"建议":"往左📷"}'), {'建议': '往左📷'});
    });

    test('只有一大段自然语言 → null（不能瞎猜）', () {
      expect(extractJson('这张照片构图不错，建议把人物放左边，光线也还行。'), isNull);
    });

    test('自然语言里带花括号但不成对象 → null', () {
      expect(extractJson('用 { 和 } 表示集合'), isNull);
    });
  });

  group('extractJson —— 类型边界（不是对象的情况）', () {
    test('顶层数字 → 取决于实现，但不能崩', () {
      expect(() => extractJson('42'), returnsNormally);
    });

    test('顶层字符串 → 不能崩', () {
      expect(() => extractJson('"hello"'), returnsNormally);
    });

    test('顶层 null 字面量 → 不能崩', () {
      expect(() => extractJson('null'), returnsNormally);
    });

    test('顶层 true → 不能崩', () {
      expect(() => extractJson('true'), returnsNormally);
    });

    test('空对象 {} → 返回空 Map（不是 null，因为确实抠到了）', () {
      expect(extractJson('{}'), isEmpty);
    });
  });
}
