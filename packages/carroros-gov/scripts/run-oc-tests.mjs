#!/usr/bin/env node
/**
 * run-oc-tests.mjs — OpenCode 环境 CarrorOS 治理测试入口
 *
 * 在 OC 上跑 CC 的测试脚本（shell/Python 级别），通过 child_process 执行。
 * 不需要 jest/vitest——测试本身是 shell/Python 的。
 *
 * 用法：
 *   node scripts/run-oc-tests.mjs           # 跑全部
 *   node scripts/run-oc-tests.mjs deep       # 只跑 Deep Runtime
 *   node scripts/run-oc-tests.mjs smoke      # 只跑 Harness Smoke
 *   node scripts/run-oc-tests.mjs all        # 全量（8 套件）
 */

import { spawnSync, execSync } from "child_process";
import { existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PKG_ROOT = resolve(__dirname, "..");
const SCRIPTS_DIR = resolve(PKG_ROOT, "src/scripts");
const CARROROS_ROOT = resolve(PKG_ROOT, "../.."); // 指向 ~/Desktop/Sylph/Carror_OS/

// ─── 测试套件注册表 ────────────────────────────────────────
const SUITES = {
  "capability-matrix": {
    script: "capability-matrix-test.sh",
    type: "bash",
    name: "Capability Matrix",
    filter: null,
  },
  "deep-runtime": {
    script: "deep-runtime-test.sh",
    type: "bash",
    name: "Deep Runtime",
    filter: null,
  },
  "harness-smoke": {
    script: "harness-smoke-test.py",
    type: "python",
    name: "Harness Smoke",
    filter: null,
  },
  "tier2": {
    script: "tier2-runtime-test.sh",
    type: "bash",
    name: "Tier 2 (配对验证)",
    filter: null,
  },
  "tier3": {
    script: "tier3-runtime-test.sh",
    type: "bash",
    name: "Tier 3 (管线验证)",
    filter: null,
  },
  "tier4": {
    script: "tier4-e2e-test.sh",
    type: "bash",
    name: "Tier 4 (端到端)",
    filter: null,
  },
  "red-team": {
    script: "ed-red-team-test.sh",
    type: "bash",
    name: "ED Red Team",
    filter: null,
  },
  "race": {
    script: "test_race.sh",
    type: "bash",
    name: "Race Condition",
    filter: null,
  },
  "audit-hooks": {
    script: "audit-hooks.sh",
    type: "bash",
    name: "Audit Hooks",
    filter: null,
  },
};

const ALL_SUITES = Object.keys(SUITES);
const FILTER = process.argv[2]?.toLowerCase() || "all";

function shouldRun(suiteKey) {
  if (FILTER === "all") return true;
  return suiteKey.includes(FILTER);
}

// ─── 运行一个套件 ────────────────────────────────────────
function runSuite(key, suite) {
  const scriptPath = resolve(SCRIPTS_DIR, suite.script);
  if (!existsSync(scriptPath)) {
    return { key, name: suite.name, status: "SKIP", detail: `文件不存在: ${suite.script}` };
  }

  let cmd, args;
  if (suite.type === "python") {
    cmd = "python3";
    args = [scriptPath];
  } else if (suite.type === "bash") {
    cmd = "bash";
    args = [scriptPath];
  }

  // 确保 CARROROS_TEST_DIR 环境变量指向 CarrorOS 仓库根目录
  const env = {
    ...process.env,
    CARROROS_TEST_DIR: CARROROS_ROOT,
    HERMES_OS_HOME: process.env.HOME,
  };

  const start = Date.now();
  const result = spawnSync(cmd, args, {
    cwd: CARROROS_ROOT, // <- 关键修改：设置为仓库根，而非 OC 包目录
    env,
    stdio: ["ignore", "pipe", "pipe"],
    timeout: 120_000,
    encoding: "utf-8",
  });
  const elapsed = ((Date.now() - start) / 1000).toFixed(1);

  const outputAll = (result.stdout || "") + (result.stderr ? `\n[STDERR]\n${result.stderr}` : "");

  // 从输出提取 PASS/FAIL 计数 — 跟 CC harness-full-test.sh parse_summary 走一样的逻辑
  // 去掉 ANSI 转义
  const cleanOutput = outputAll.replace(/\u001b\[[0-9;]*m/g, '');
  
  function extractCount(regex, groupIndex = 1) {
    const m = cleanOutput.match(regex);
    return m ? parseInt(m[groupIndex]) : null;
  }

  let passCount = null, failCount = null;

  // 格式1: "summary: X/Y passed, Z failed"
  const m1 = cleanOutput.match(/^summary: (\d+)\/(\d+) passed, (\d+) failed/m);
  if (m1) { passCount = parseInt(m1[1]); failCount = parseInt(m1[3]); }
  
  // 格式2: "Tier N: X/Y passed, Z failed" / "Deep Runtime: X/Y passed, Z failed"
  if (passCount === null) {
    const m2 = cleanOutput.match(/(?:Tier [234]|Deep Runtime):.*?(\d+)\/(\d+) passed, (\d+) failed/);
    if (m2) { passCount = parseInt(m2[1]); failCount = parseInt(m2[3]); }
  }
  
  // 格式3: "Checks: N pass  N fail"
  if (passCount === null) {
    const m3 = cleanOutput.match(/Checks:\s*(\d+)\s+pass\s+(\d+)\s+fail/);
    if (m3) { passCount = parseInt(m3[1]); failCount = parseInt(m3[2]); }
  }
  
  // 格式4: "结果: X 通过 / Y 失败 / 共 Z 断言" (ED Red Team)
  if (passCount === null) {
    const m4 = cleanOutput.match(/结果:\s*(\d+)\s+通过\s*\/\s*(\d+)\s+失败/);
    if (m4) { passCount = parseInt(m4[1]); failCount = parseInt(m4[2]); }
  }
  
  // 格式5: "Results: X PASS / Y FAIL / Z SKIP" (Race Condition)
  if (passCount === null) {
    const m5 = cleanOutput.match(/Results:\s*(\d+)\s+PASS\s*\/\s*(\d+)\s+FAIL/);
    if (m5) { passCount = parseInt(m5[1]); failCount = parseInt(m5[2]); }
  }
  
  // 格式6: "Results: PASS=N FAIL=N" (Harness Smoke)
  if (passCount === null) {
    const m6 = cleanOutput.match(/Results:\s*PASS=(\d+)\s+FAIL=(\d+)/);
    if (m6) { passCount = parseInt(m6[1]); failCount = parseInt(m6[2]); }
  }

  const status =
    result.status === 0 || (result.status === null && result.signal)
      ? "PASS"
      : result.error?.code === "ETIMEDOUT"
      ? "TIMEOUT"
      : "FAIL";

  return {
    key,
    name: suite.name,
    status,
    exitCode: result.status,
    elapsed: `${elapsed}s`,
    passCount,
    failCount,
    /** 全量输出（完整日志） */
    rawOutput: outputAll,
  };
}

// ─── 主流程 ────────────────────────────────────────────────
function main() {
  console.log(`\n═══════════════════════════════════════`);
  console.log(`  @carroros/gov — OC 测试入口`);
  console.log(`  仓库: ${CARROROS_ROOT}`);
  console.log(`  包: ${PKG_ROOT}`);
  console.log(`  CWD: ${CARROROS_ROOT}`);
  console.log(`  筛选: ${FILTER === "all" ? "全量" : FILTER}`);
  console.log(`═══════════════════════════════════════\n`);

  const results = [];
  for (const key of ALL_SUITES) {
    if (shouldRun(key)) {
      const r = runSuite(key, SUITES[key]);
      results.push(r);
    }
  }

  // ─── 原始日志展区 ────────────────────────────────────────
  console.log(`\n═══════════════════════════════════════`);
  console.log(`  详细运行日志`);
  console.log(`═══════════════════════════════════════\n`);

  for (const r of results) {
    const sep = "━".repeat(50);
    console.log(`\n${sep}`);
    console.log(`  ${r.name} (${r.elapsed}) ` + (r.status === "PASS" ? "✅" : r.status === "FAIL" || r.status === "TIMEOUT" ? "❌" : "⏭️"));
    console.log(`${sep}`);
    if (r.rawOutput) {
      console.log(r.rawOutput);
    }
  }

  // ─── 汇总 ──────────────────────────────────────────────
  console.log(`\n═══════════════════════════════════════`);
  console.log(`  测试报告 @carroros/gov on OC`);
  console.log(`═══════════════════════════════════════\n`);

  const suitesPassed = results.filter((r) => r.status === "PASS").length;
  const suitesFailed = results.filter((r) => r.status === "FAIL" || r.status === "TIMEOUT").length;
  const suitesSkipped = results.filter((r) => r.status === "SKIP").length;
  const totalPass = results.reduce((sum, r) => sum + (r.passCount ?? 0), 0);
  const totalFail = results.reduce((sum, r) => sum + (r.failCount ?? 0), 0);

  for (const r of results) {
    const icon =
      r.status === "PASS" ? "✅" : r.status === "FAIL" || r.status === "TIMEOUT" ? "❌" : "⏭️";
    console.log(`  ${icon} ${r.name} (${r.elapsed})  PASS=${r.passCount ?? "?"} FAIL=${r.failCount ?? "?"}`);
  }

  console.log(`  ─────────────────────────────`);
  console.log(`  ✅ PASS: ${suitesPassed}/${ALL_SUITES.length} suites (断言: ${totalPass})`);
  console.log(`  ❌ FAIL: ${suitesFailed}/${ALL_SUITES.length} suites (断言: ${totalFail})`);
  console.log(`  ⏭️ SKIP: ${suitesSkipped}/${ALL_SUITES.length} suites`);
  console.log(`  📊 总断言: ${totalPass + totalFail} (${totalPass}/${totalPass + totalFail} passed)`);
  console.log(`═══════════════════════════════════════\n`);

  process.exit(totalFail > 0 ? 1 : 0);
}

main();
