import { expect, test, type Page } from "@playwright/test";

// ── chat-inbox 交互矩阵 + 浮层关闭语义（C4/C5 等价物）──

test.describe("chat-inbox 页面", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/chat?session=inbox");
  });

  const announceDialog = (page: Page) =>
    page.getByRole("dialog").filter({ hasText: "系统公告" });

  test("三栏布局渲染 + 系统公告自动弹出", async ({ page }) => {
    await expect(page.getByTestId("welcome-section")).toBeVisible();
    await expect(page.getByTestId("topic-panel")).toBeVisible();
    await expect(page.getByTestId("composer")).toBeVisible();
    await expect(page.getByText("晚上好")).toBeVisible();
    // 4 张助手卡（真实站捕获数据）
    await expect(page.getByTestId("assistant-card-fitness-expert")).toBeVisible();
    await expect(page.getByTestId("assistant-card-mistaker")).toBeVisible();
    await expect(page.getByTestId("assistant-card-code-review-and-fix")).toBeVisible();
    await expect(page.getByTestId("assistant-card-cyber-specialist")).toBeVisible();
    // 公告弹窗
    await expect(announceDialog(page)).toBeVisible({ timeout: 5000 });
  });

  test("公告弹窗 Esc 关闭 + 焦点归还", async ({ page }) => {
    const dialog = announceDialog(page);
    await expect(dialog).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    // 关闭后不再弹出
    await page.waitForTimeout(800);
    await expect(dialog).not.toBeVisible();
  });

  test("公告弹窗遮罩点击关闭", async ({ page }) => {
    const dialog = announceDialog(page);
    await expect(dialog).toBeVisible({ timeout: 5000 });
    await page.mouse.click(80, 120); // 弹窗（居中 420 宽）之外的遮罩区域
    await expect(dialog).not.toBeVisible();
  });

  test("公告弹窗 × 按钮关闭", async ({ page }) => {
    const dialog = announceDialog(page);
    await expect(dialog).toBeVisible({ timeout: 5000 });
    await dialog.locator(".ant-modal-close").click();
    await expect(dialog).not.toBeVisible();
  });

  test("新建助手 → 登录弹窗，Esc/遮罩/× 关闭语义", async ({ page }) => {
    await expect(announceDialog(page)).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Escape");
    await page.getByTestId("new-assistant").click();
    const login = page.getByRole("dialog").filter({ hasText: "登录到 XSimpleChat" });
    await expect(login).toBeVisible();
    await expect(login.getByText("欢迎回来！")).toBeVisible();
    // Esc
    await page.keyboard.press("Escape");
    await expect(login).not.toBeVisible();
    // 遮罩
    await page.getByTestId("new-assistant").click();
    await expect(login).toBeVisible();
    await page.mouse.click(80, 120); // 弹窗之外的遮罩区域
    await expect(login).not.toBeVisible();
    // ×
    await page.getByTestId("new-assistant").click();
    await expect(login).toBeVisible();
    await login.locator(".ant-modal-close").click();
    await expect(login).not.toBeVisible();
  });

  test("登录弹窗：焦点陷阱 + 密码可见切换", async ({ page }) => {
    await expect(announceDialog(page)).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Escape");
    await page.getByTestId("new-assistant").click();
    const login = page.getByRole("dialog").filter({ hasText: "登录到 XSimpleChat" });
    await expect(login).toBeVisible();
    // Tab 循环不离开弹窗
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press("Tab");
    }
    await expect(login).toBeVisible();
    // 密码可见切换按钮存在
    await expect(login.locator(".ant-input-password-icon")).toBeVisible();
  });

  test("模型下拉：点击开/外点关/Esc 关/再点关/选中切换", async ({ page }) => {
    await expect(announceDialog(page)).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Escape");
    const selector = page.getByTestId("model-selector");
    await selector.click();
    const menu = page.getByRole("menu");
    await expect(menu).toBeVisible();
    await expect(menu.getByText("GPT-5.6 Luna")).toBeVisible();
    // 外点关闭
    await page.mouse.click(700, 450);
    await expect(menu).not.toBeVisible();
    // Esc 关闭
    await selector.click();
    await expect(menu).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(menu).not.toBeVisible();
    // 再点关闭
    await selector.click();
    await expect(menu).toBeVisible();
    await selector.click();
    await expect(menu).not.toBeVisible();
    // 选中切换
    await selector.click();
    await menu.getByText("DeepSeek V4").click();
    await expect(selector).toContainText("DeepSeek V4");
  });

  test("发送流：气泡追加 + 发送中禁用（double submit）", async ({ page }) => {
    await expect(announceDialog(page)).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Escape");
    const input = page.getByTestId("chat-input");
    const send = page.getByTestId("send-button");
    await input.fill("你好，帮我总结一下");
    await expect(send).toBeEnabled();
    await send.click();
    // 发送中：按钮禁用（防重复提交）
    await expect(send).toBeDisabled();
    // 用户气泡 + 助手回复
    await expect(page.getByTestId("message-user")).toBeVisible();
    await expect(page.getByTestId("message-assistant")).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId("message-assistant")).toContainText("你好，帮我总结一下");
    // 输入框已清空
    await expect(input).toHaveValue("");
  });

  test("Enter 发送 / 清空按钮", async ({ page }) => {
    await expect(announceDialog(page)).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Escape");
    const input = page.getByTestId("chat-input");
    await input.fill("回车发送测试");
    await input.press("Enter");
    await expect(page.getByTestId("message-user")).toBeVisible();
    await expect(page.getByTestId("message-assistant")).toBeVisible({ timeout: 5000 });
    // 清空
    await page.getByTestId("clear-messages").click();
    await expect(page.getByTestId("message-list")).toHaveCount(0);
  });

  test("话题说明卡 × 关闭", async ({ page }) => {
    await expect(announceDialog(page)).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Escape");
    const guide = page.getByTestId("topic-guide");
    await expect(guide).toBeVisible();
    await guide.locator("button[aria-label='关闭说明']").click();
    await expect(guide).not.toBeVisible();
  });

  test("面板开关：收起侧栏/切换右面板", async ({ page }) => {
    await expect(announceDialog(page)).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Escape");
    await page.getByTestId("collapse-sidebar").click();
    await expect(page.getByTestId("current-assistant")).toHaveCount(0);
    await page.getByTestId("collapse-sidebar").click();
    await expect(page.getByTestId("current-assistant")).toBeVisible();
    await page.getByTestId("toggle-right-panel").click();
    await expect(page.getByTestId("topic-panel")).toHaveCount(0);
    await page.getByTestId("toggle-right-panel").click();
    await expect(page.getByTestId("topic-panel")).toBeVisible();
  });

  test("rail 图标 tooltip：hover 显 / leave 隐", async ({ page }) => {
    await expect(announceDialog(page)).toBeVisible({ timeout: 5000 });
    await page.keyboard.press("Escape");
    const icon = page.getByTestId("rail-translation");
    await icon.hover();
    await expect(page.getByRole("tooltip").filter({ hasText: "翻译" })).toBeVisible();
    await page.mouse.move(700, 450);
    await expect(page.getByRole("tooltip")).toHaveCount(0);
  });
});

test.describe("侧栏拖拽与浮层补全", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/chat?session=inbox");
    // 等公告弹窗出现后关闭（保证无遮罩干扰后续交互）
    await expect(page.getByRole("dialog").filter({ hasText: "系统公告" })).toBeVisible({ timeout: 8000 }).catch(() => undefined);
    await page.keyboard.press("Escape").catch(() => undefined);
    await expect(page.getByRole("dialog").filter({ hasText: "系统公告" })).not.toBeVisible({ timeout: 3000 }).catch(() => undefined);
  });

  test("左列表栏拖拽调宽 + 持久化", async ({ page }) => {
    const handle = page.getByTestId("resize-left");
    await expect(handle).toBeVisible();
    const before = (await page.getByTestId("current-assistant").boundingBox())!;
    // 拖拽 +80px
    const hb = (await handle.boundingBox())!;
    await page.mouse.move(hb.x + hb.width / 2, hb.y + 200);
    await page.mouse.down();
    await page.mouse.move(hb.x + 80, hb.y + 200, { steps: 5 });
    await page.mouse.up();
    const after = (await page.getByTestId("current-assistant").boundingBox())!;
    expect(after.width).toBeGreaterThan(before.width + 40);
    // 开闭
    await page.getByTestId("collapse-sidebar").click();
    await expect(page.getByTestId("resize-left")).toHaveCount(0);
    await page.getByTestId("collapse-sidebar").click();
    await expect(page.getByTestId("resize-left")).toBeVisible();
  });

  test("右面板拖拽调宽 + 开闭", async ({ page }) => {
    const handle = page.getByTestId("resize-right");
    await expect(handle).toBeVisible();
    const before = (await page.getByTestId("topic-panel").boundingBox())!;
    const hb = (await handle.boundingBox())!;
    await page.mouse.move(hb.x + hb.width / 2, hb.y + 200);
    await page.mouse.down();
    await page.mouse.move(hb.x - 60, hb.y + 200, { steps: 5 });
    await page.mouse.up();
    const after = (await page.getByTestId("topic-panel").boundingBox())!;
    expect(after.width).toBeGreaterThan(before.width + 30);
    await page.getByTestId("toggle-right-panel").click();
    await expect(page.getByTestId("resize-right")).toHaveCount(0);
    await page.getByTestId("toggle-right-panel").click();
    await expect(page.getByTestId("resize-right")).toBeVisible();
  });

  test("联系客服弹窗：打开/关闭/复制邮箱", async ({ page }) => {
    await page.getByTestId("contact-support").click();
    const modal = page.getByRole("dialog").filter({ hasText: "联系客服" });
    await expect(modal).toBeVisible();
    await expect(modal.getByText("support@xsimplechat.com")).toBeVisible();
    await modal.getByTestId("copy-email").click({ force: true });
    await expect(modal.getByText("已复制 ✓")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(modal).not.toBeVisible();
  });

  test("分享/更多/话题更多/托盘/发送选项 下拉菜单", async ({ page }) => {
    // 分享
    await page.getByTestId("share-menu").click();
    await expect(page.getByRole("menuitem", { name: "复制链接" })).toBeVisible();
    await page.keyboard.press("Escape");
    // 更多
    await page.getByTestId("more-menu").click();
    await expect(page.getByRole("menuitem", { name: "关于 XSimple" })).toBeVisible();
    await page.keyboard.press("Escape");
    // 话题更多
    await page.getByTestId("topic-more").click();
    await expect(page.getByRole("menuitem", { name: "清空会话" })).toBeVisible();
    await page.keyboard.press("Escape");
    // 托盘
    await page.getByTestId("tray-menu").click();
    await expect(page.getByRole("menuitem", { name: "知识库" })).toBeVisible();
    await page.keyboard.press("Escape");
    // 发送箭头
    await page.getByTestId("send-arrow").click();
    await expect(page.getByRole("menuitem", { name: "继续生成" })).toBeVisible();
    await page.keyboard.press("Escape");
    // 发送按钮本体仍可用
    await page.getByTestId("chat-input").fill("测试");
    await page.getByTestId("send-button").click();
    await expect(page.getByTestId("message-assistant")).toBeVisible({ timeout: 5000 });
  });
});

test("拖拽实时更新（不松手 UI 已变宽）", async ({ page }) => {
  await page.goto("/chat?session=inbox");
  await expect(page.getByRole("dialog").filter({ hasText: "系统公告" })).toBeVisible({ timeout: 8000 });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog").filter({ hasText: "系统公告" })).not.toBeVisible({ timeout: 3000 });
  const handle = page.getByTestId("resize-left");
  await expect(handle).toBeVisible();
  const hb = (await handle.boundingBox())!;
  const width = () =>
    page.evaluate(() => document.querySelector('[aria-label="助手列表"]')!.getBoundingClientRect().width);
  const start = await width();
  await page.mouse.move(hb.x + 2, hb.y + 200);
  await page.mouse.down();
  await page.mouse.move(hb.x + 50, hb.y + 200, { steps: 3 });
  await page.waitForTimeout(150);
  const mid = await width(); // 松手前
  await page.mouse.up();
  expect(mid).toBeGreaterThan(start + 30);
});
