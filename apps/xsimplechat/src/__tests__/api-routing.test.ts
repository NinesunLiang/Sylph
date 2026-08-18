import { describe, expect, it } from "vitest";
import { api } from "@/shared/api/api-routing";

describe("api-routing mock 层（inferred 契约）", () => {
  it("listAssistants 返回 4 个真实站捕获助手", async () => {
    const list = await api.listAssistants();
    expect(list).toHaveLength(4);
    expect(list.map((a) => a.name)).toEqual([
      "健身专家",
      "Mistaker",
      "代码优化/错误修改",
      "伦理安全分析师",
    ]);
  });

  it("getTopics 返回默认话题（临时）", async () => {
    const topics = await api.getTopics("inbox");
    expect(topics[0]).toMatchObject({ title: "默认话题", tag: "临时" });
  });

  it("listModels 首位为 GPT-5.6 Luna", async () => {
    const models = await api.listModels();
    expect(models[0].name).toBe("GPT-5.6 Luna");
  });

  it("getAnnouncement 返回系统公告", async () => {
    const ann = await api.getAnnouncement();
    expect(ann?.title).toBe("系统公告");
  });

  it("sendMessage 返回 mock 回复（含原文）", async () => {
    const reply = await api.sendMessage({ sessionId: "inbox", content: "你好", model: "gpt-5.6-luna" });
    expect(reply.role).toBe("assistant");
    expect(reply.content).toContain("你好");
  });
});
