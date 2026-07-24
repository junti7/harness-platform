import assert from "node:assert/strict";
import harnessBridge from "../plugins/harness-bridge/index.js";
import {
  collectHarnessWorkspaceStats,
  resolveHarnessPath,
  isDirectSajuNotebookQuery,
  isShellTool,
  shouldEnforceHarnessKnowledge,
  shouldEnforceSajuBridge,
  shouldEnforceWorkspaceStats,
  validateWorkspaceCommand,
} from "../plugins/harness-bridge/index.js";

assert.equal(shouldEnforceSajuBridge("오늘 사주 운세 알려줘"), true);
assert.deepEqual(
  shouldEnforceSajuBridge("그럼 시간대는?", [
    { role: "assistant", content: "사주명리학자료 기준 오늘 일진" },
  ]),
  true,
);
assert.equal(shouldEnforceSajuBridge("오늘 날씨 알려줘"), false);
assert.equal(
  shouldEnforceSajuBridge("오늘 날씨 알려줘", [
    { role: "assistant", content: "사주명리학자료 기준 오늘 일진" },
  ]),
  false,
);

assert.equal(
  isDirectSajuNotebookQuery("bash", {
    command:
      "nlm notebook query d3fe3696-ff81-4810-94a8-9584c329c440 'question'",
  }),
  true,
);
assert.equal(
  isDirectSajuNotebookQuery("bash", {
    command: "nlm notebook query another-notebook 'question'",
  }),
  false,
);
assert.equal(
  isDirectSajuNotebookQuery("bash", {
    command: "a=nlm; b=notebook; c=query; $a $b $c $NOTEBOOK_ID",
  }),
  false,
);
assert.equal(
  isDirectSajuNotebookQuery(
    "bash",
    { command: "a=nlm; b=notebook; c=query; $a $b $c $NOTEBOOK_ID" },
    true,
  ),
  true,
);
assert.equal(
  isDirectSajuNotebookQuery("mcp__notebooklm__notebook_query", {
    notebook_id: "d3fe3696-ff81-4810-94a8-9584c329c440",
  }),
  true,
);
assert.equal(
  isDirectSajuNotebookQuery("mcp__notebooklm__notebook_query", {
    notebook_id: "another-notebook",
  }),
  false,
);
assert.equal(
  isDirectSajuNotebookQuery(
    "mcp__notebooklm__notebook_query",
    { notebook_id: "another-notebook" },
    true,
  ),
  true,
);

const circular = {};
circular.self = circular;
assert.equal(isDirectSajuNotebookQuery("bash", circular), true);
assert.equal(isDirectSajuNotebookQuery("weather", circular), false);
assert.equal(
  shouldEnforceSajuBridge("그럼 시간대는?", [
    { role: "assistant", content: circular },
  ]),
  true,
);

assert.equal(isShellTool("terminal_command"), true);
assert.equal(isShellTool("message"), false);
assert.equal(
  shouldEnforceWorkspaceStats("mac mini의 harness-project 폴더 내 파일들의 전체 용량은?"),
  true,
);
assert.equal(shouldEnforceWorkspaceStats("Mac mini 전체 디스크 용량은?"), false);
assert.equal(shouldEnforceHarnessKnowledge("현재 Turtle Trading 진행 상태 알려줘"), true);
assert.equal(shouldEnforceHarnessKnowledge("자료 수입과 교육 사업 현황 알려줘"), true);
assert.equal(shouldEnforceHarnessKnowledge("스마트팜 센서 구성은?"), true);
assert.equal(shouldEnforceHarnessKnowledge("ESP8255에 연결된 것들 알려줘."), true);
assert.equal(shouldEnforceHarnessKnowledge("ESP8266 핀 배선은?"), true);
assert.equal(shouldEnforceHarnessKnowledge("ESP8266 가격은?"), false);
assert.equal(shouldEnforceHarnessKnowledge("ESP8266 dashboard 디자인은?"), false);
assert.equal(shouldEnforceHarnessKnowledge("오늘 날씨 알려줘"), false);
assert.throws(() => resolveHarnessPath("../outside"), /path_outside_harness_workspace/);
assert.deepEqual(validateWorkspaceCommand(["git", "status", "--short"]), [
  "/usr/bin/git",
  "status",
  "--short",
]);
assert.throws(
  () => validateWorkspaceCommand(["git", "reset", "--hard"]),
  /command_not_in_safe_verification_allowlist/,
);
assert.throws(
  () => validateWorkspaceCommand(["python3", "-c", "open('/tmp/x','w').write('x')"]),
  /command_not_in_safe_verification_allowlist/,
);
assert.throws(
  () => validateWorkspaceCommand(["node", "-e", "process.exit(0)"]),
  /command_not_in_safe_verification_allowlist/,
);
assert.throws(
  () => validateWorkspaceCommand(["/tmp/git", "status"]),
  /ENOENT|untrusted_executable_path/,
);

const hooks = new Map();
const toolNames = [];
harnessBridge.register({
  registerTool(tool) {
    toolNames.push(tool.name);
  },
  on(name, handler) {
    hooks.set(name, handler);
  },
});
assert.deepEqual(
  toolNames.sort(),
  [
    "harness_alpaca_status",
    "harness_calendar_create",
    "harness_calendar_list",
    "harness_cron_create",
    "harness_cron_list",
    "harness_cron_remove",
    "harness_gmail_get",
    "harness_gmail_search",
    "harness_knowledge_query",
    "harness_saju_query",
    "harness_workspace_exec",
    "harness_workspace_read",
    "harness_workspace_search",
    "harness_workspace_stats",
    "harness_workspace_write",
  ],
);
const workspaceStats = await collectHarnessWorkspaceStats("plugins/harness-bridge");
assert.equal(workspaceStats.path, "plugins/harness-bridge");
assert.ok(workspaceStats.files >= 1);
assert.ok(workspaceStats.allocatedBytes > 0);
assert.ok(workspaceStats.durationMs < 30_000);
const context = { runId: "run-saju-1", sessionKey: "session-saju-1" };
const sajuRouting = await hooks.get("before_prompt_build")(
  { prompt: "오늘 사주 운세 알려줘", messages: [], runId: "run-saju-1" },
  context,
);
assert.match(sajuRouting.appendSystemContext, /HARNESS SAJU ROUTING/);
const openClawSajuRouting = await hooks.get("before_prompt_build")(
  { prompt: "OpenClaw에서 오늘 사주 운세 알려줘", messages: [], runId: "run-saju-2" },
  { runId: "run-saju-2", sessionKey: "session-saju-2" },
);
assert.match(openClawSajuRouting.appendSystemContext, /HARNESS SAJU ROUTING/);
assert.deepEqual(
  await hooks.get("before_tool_call")(
    {
      toolName: "bash",
      params: { command: "a=nlm; $a notebook query $NOTEBOOK_ID question" },
      runId: "run-saju-1",
    },
    context,
  ),
  {
    block: true,
    blockReason:
      "Direct Saju NotebookLM queries are blocked; use the privacy-safe cached Harness bridge.",
  },
);
await hooks.get("agent_end")({ runId: "run-saju-1" }, context);
assert.deepEqual(
  await hooks.get("before_tool_call")(
    {
      toolName: "bash",
      params: { command: "a=nlm; $a notebook query $NOTEBOOK_ID question" },
      runId: "run-saju-1",
    },
    context,
  ),
  undefined,
);

const knowledgeContext = {
  runId: "run-knowledge-1",
  sessionKey: "session-knowledge-1",
};
const knowledgeRouting = await hooks.get("before_prompt_build")(
  {
    prompt: "Harness의 교육 사업과 스마트팜 현황 알려줘",
    messages: [],
    runId: "run-knowledge-1",
  },
  knowledgeContext,
);
assert.match(knowledgeRouting.appendSystemContext, /HARNESS KNOWLEDGE ROUTING/);
assert.deepEqual(
  await hooks.get("before_tool_call")(
    {
      toolName: "harness_knowledge_query",
      params: { question: "교육 사업과 스마트팜 현황" },
      runId: "run-knowledge-1",
    },
    knowledgeContext,
  ),
  {
    params: {
      question: "Harness의 교육 사업과 스마트팜 현황 알려줘",
      reuseOnly: false,
    },
  },
);
assert.deepEqual(
  await hooks.get("before_tool_call")(
    {
      toolName: "harness_knowledge_query",
      params: { question: "스마트팜만 다시 검색" },
      runId: "run-knowledge-1",
    },
    knowledgeContext,
  ),
  {
    params: {
      question: "Harness의 교육 사업과 스마트팜 현황 알려줘",
      reuseOnly: true,
    },
  },
);
await hooks.get("agent_end")({ runId: "run-knowledge-1" }, knowledgeContext);

const hardwareKnowledgeContext = {
  runId: "run-hardware-knowledge-1",
  sessionKey: "session-hardware-knowledge-1",
};
const hardwareKnowledgeRouting = await hooks.get("before_prompt_build")(
  {
    prompt: "ESP8255에 연결된 것들 알려줘.",
    messages: [],
    runId: "run-hardware-knowledge-1",
  },
  hardwareKnowledgeContext,
);
assert.match(hardwareKnowledgeRouting.appendSystemContext, /HARNESS KNOWLEDGE ROUTING/);
assert.deepEqual(
  await hooks.get("before_tool_call")(
    {
      toolName: "memory_search",
      params: { query: "ESP8255" },
      runId: "run-hardware-knowledge-1",
    },
    hardwareKnowledgeContext,
  ),
  {
    block: true,
    blockReason:
      "Harness knowledge routing is active; call harness_knowledge_query once and answer from its canonical evidence without memory, shell, or workspace-search fallback.",
  },
);
assert.deepEqual(
  await hooks.get("before_tool_call")(
    {
      toolName: "bash",
      params: { command: "rg ESP8255 ." },
      runId: "run-hardware-knowledge-1",
    },
    hardwareKnowledgeContext,
  ),
  {
    block: true,
    blockReason:
      "Harness knowledge routing is active; call harness_knowledge_query once and answer from its canonical evidence without memory, shell, or workspace-search fallback.",
  },
);
assert.deepEqual(
  await hooks.get("before_tool_call")(
    {
      toolName: "harness_workspace_search",
      params: { query: "ESP8255" },
      runId: "run-hardware-knowledge-1",
    },
    hardwareKnowledgeContext,
  ),
  {
    block: true,
    blockReason:
      "Harness knowledge routing is active; call harness_knowledge_query once and answer from its canonical evidence without memory, shell, or workspace-search fallback.",
  },
);
assert.equal(
  await hooks.get("before_tool_call")(
    {
      toolName: "memory_search",
      params: { query: "weather" },
      runId: "run-ordinary-1",
    },
    {
      runId: "run-ordinary-1",
      sessionKey: "session-ordinary-1",
    },
  ),
  undefined,
);
await hooks.get("agent_end")(
  { runId: "run-hardware-knowledge-1" },
  hardwareKnowledgeContext,
);
