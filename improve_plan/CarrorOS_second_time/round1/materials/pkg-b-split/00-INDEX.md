# PKG-B 函数级分片索引

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | 生成: 2026-07-19
> 拆分规则:只按函数/文件边界切,不切任何函数体;行号=原文件真实行号;全部脱敏。

## 阅读顺序与验收要点

| 文件 | 内容 | gpt 需求映射 |
|---|---|---|
| 01-04 | carros_base.py 四分 | **cmd_verify 完整函数在 02**(788-864) |
| 05-06 | pretool-gate.py 两分 | **_check_verified 在 05**(254-278);verify-gate 门在 06(543-) |
| 07 | verify_gate.py 全文 | 点名证据 |
| 08-09 | oracle_gate/oracle_engine 双副本 | 孤儿裁决+双源实证 |
| 10-11 | 其余验证实现+测试 | 六处重复验证取证 |
| 12 | grep 证据集 | --pipeline/R6/调用点行号 |
| 13 | git 信息 | ls-files/status/HEAD |
| 14 | skill 契约+注册表 | 验证契约统一范围 |
| 15 | hook 配置+脚本 | 注册与执行约定 |

## 完整性校验

```
1f03c864f615c094df681e4f3c74632b8713de4169972627e48fced2fe48144d  01-carros_base-part1.md
eaf141c94642fb4a34aa02b19e445c7c85302476cc226a554b537d2593f31551  02-carros_base-part2.md
04815d28b29ce7c99ae6c555e8b495b4bdb84e6f4b5d8e6783d521c6fd6871c0  03-carros_base-part3.md
4d8e18c36bc5f7a4dd183e17dbcd86c4a30e9e19ed890a459752437a2e21483c  04-carros_base-part4.md
a25c778581a7734c4f77d9d176297f51bdcf114ee85187322ba1f6a1161e7084  05-pretool-gate-part1.md
bc8967c5baddbdd0af3d7aad0160019d7aab06b607e7f38fd48f61d33ede0a17  06-pretool-gate-part2.md
31c78bf244ff9a15a421bf9a0758b760dd2862eb6e35330768bb72b713ab7d9d  07-verify_gate-full.md
1c1617f3948b56e6d716d37ad8cafa4f1a265702a62853451300b4b5f448a2cf  08-oracle_gate-both.md
991590615ec508d4c0ea7edbeb38aa1ac961d276292a6c7a9a5374927977f89d  09-oracle_engine-both.md
066aa2f6eb4730c90d8c9ac6bcaf7c5b6f333965f6b6473ed050ec76b8d5dd80  10-runtime_verify.md
bd5eac730a41d0421a3f7b772f38e4682e991b8028d83fb8919f53a43235d9fd  11-verify-tests.md
1af0e11c4e9aeb19d79c5d47f12f3f22e87a78da15d25a20192d097320eb3efb  12-grep-evidence.md
f31eb8192a20f7ea096ba647d811eb58953687d6d8beedbc2545c66ef7bf15a6  13-git-info.md
9430837a6e85c0826d07d8128d6e24998fbbd2b4a4685044844f390646639313  14-skills-and-registries.md
43f3e0f914823489f9a9397c9ba2dc78be2029f127d0e7df803361d1f30ba20a  15-settings-and-hooks.md
```

## 字节数

```
   25536 01-carros_base-part1.md
   14951 02-carros_base-part2.md
   32118 03-carros_base-part3.md
   29282 04-carros_base-part4.md
   24363 05-pretool-gate-part1.md
   15305 06-pretool-gate-part2.md
   18513 07-verify_gate-full.md
    9828 08-oracle_gate-both.md
   36438 09-oracle_engine-both.md
   21194 10-runtime_verify.md
   59590 11-verify-tests.md
   43023 12-grep-evidence.md
   62226 13-git-info.md
   54113 14-skills-and-registries.md
   37393 15-settings-and-hooks.md
  486162 total
```
