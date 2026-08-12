import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SKILL = (ROOT / ".claude/skills/lx-goal/SKILL.md").read_text(encoding="utf-8")
PHASE0 = (ROOT / ".claude/skills/lx-goal/references/phase0-activation.md").read_text(encoding="utf-8")


class Phase0ClarificationCardsTest(unittest.TestCase):
    def test_skill_requires_one_question_and_re_scan_loop(self):
        self.assertIn("每张澄清卡只能包含一个待决策问题", SKILL)
        self.assertIn("用户回答当前卡后，重新扫描剩余不确定项", SKILL)
        self.assertIn("不得把尚未提问的 Q 项批量展示给用户", SKILL)

    def test_phase0_defines_convergence_not_question_count(self):
        self.assertIn("逐卡片收敛", PHASE0)
        self.assertIn("重新扫描剩余不确定项", PHASE0)
        self.assertIn("没有新的用户决策项”是澄清完成条件", PHASE0)
        self.assertNotIn("所有 Q 项一次性列出", PHASE0)
        self.assertNotIn("一次性列出所有 Q 项", PHASE0)


if __name__ == "__main__":
    unittest.main()
