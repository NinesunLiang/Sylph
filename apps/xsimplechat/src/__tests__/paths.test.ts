import { describe, expect, it } from "vitest";
import { paths } from "@/router/paths";

describe("paths 唯一出口", () => {
  it("chat 路径支持会话参数", () => {
    expect(paths.chat()).toBe("/chat");
    expect(paths.chat("inbox")).toBe("/chat?session=inbox");
  });

  it("assistant 路径编码 slug", () => {
    expect(paths.assistant("code-review-and-fix")).toBe("/discover/assistant/code-review-and-fix");
    expect(paths.assistant("a b")).toBe("/discover/assistant/a%20b");
  });

  it("固定路由正确", () => {
    expect(paths.discover).toBe("/discover");
    expect(paths.translation).toBe("/translation");
    expect(paths.files).toBe("/files");
    expect(paths.settings).toBe("/settings");
    expect(paths.member).toBe("/member");
  });
});
