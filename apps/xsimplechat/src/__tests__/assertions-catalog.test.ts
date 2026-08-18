import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

// 校验 assertions.ts 的 17 个 helper 与 assertion-catalog.yaml 一一对应
const repoRoot = path.resolve(process.cwd(), "../..");
const catalogPath = path.join(
  repoRoot,
  ".claude/workflows/frontend-overnight/scripts/carroros-gates/assertion-catalog.yaml",
);

interface CatalogEntry {
  id: string;
  helper: string;
}

function parseCatalog(text: string): CatalogEntry[] {
  // yaml 结构: `  <id>:` 后跟 `   helper: <name>`（缩进 2/3 空格）
  const entries: CatalogEntry[] = [];
  const lines = text.split("\n");
  let currentId: string | null = null;
  for (const line of lines) {
    const idMatch = line.match(/^ {2}([a-z0-9_]+):\s*$/);
    const helperMatch = line.match(/^ {4}helper:\s*"([A-Za-z0-9_]+)"\s*$/);
    if (idMatch) {
      currentId = idMatch[1];
    } else if (helperMatch && currentId) {
      entries.push({ id: currentId, helper: helperMatch[1] });
      currentId = null;
    }
  }
  return entries;
}

describe("assertion catalog 对齐（17/17）", () => {
  const catalogText = fs.readFileSync(catalogPath, "utf-8");
  const catalog = parseCatalog(catalogText);

  const assertionsSrc = fs.readFileSync(
    path.resolve(__dirname, "../../tests/e2e/helpers/assertions.ts"),
    "utf-8",
  );

  it("catalog 共 17 个断言", () => {
    expect(catalog).toHaveLength(17);
  });

  it.each(catalog)("helper $helper 已实现且 id $id 在 registry", ({ id, helper }) => {
    // 实现存在（函数声明）
    expect(assertionsSrc).toContain(`export async function ${helper}`);
    // registry 以 catalog id 为键
    expect(assertionsSrc).toMatch(new RegExp(`${id}: ${helper}`));
  });

  it("tokens scss 存在关键色值", () => {
    const colors = fs.readFileSync(
      path.resolve(__dirname, "../styles/tokens/_colors.scss"),
      "utf-8",
    );
    expect(colors).toContain("#0072f5");
    expect(colors).toContain("#f8f8f8");
    expect(colors).toContain("#222");
  });
});
