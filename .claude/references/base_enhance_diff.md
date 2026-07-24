L1和L2只是任务的复杂度和严谨程度；不管base和enhance都是有L1 L2的概念的；base是专门用于deepseek-v4-flas
  h这种中低阶模型场景，方式是通过superpower这种强规格spec，强路径方式驱动模型工作减少模型决策;而enhance是应对
  高阶模型，因为高阶模型自身能把事情处理得很好，所以避免通过superpower这种方式，而是使用 
  mattpocock/skills这种充分grill-me,充分TDD,充分checklist的逻辑，至于实现部分留给高阶模型自定义发挥；
  项目要么使用base，要么使用enhance;别混为一谈 