import assert from "node:assert/strict";
import harnessBridge from "../plugins/harness-bridge/index.js";
import {
  isDirectSajuNotebookQuery,
  isShellTool,
  shouldEnforceSajuBridge,
} from "../plugins/harness-bridge/index.js";

assert.equal(shouldEnforceSajuBridge("오늘 사주 운세 알려줘"), true);
assert.equal(
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

const hooks = new Map();
harnessBridge.register({
  registerTool() {},
  on(name, handler) {
    hooks.set(name, handler);
  },
});
const context = { runId: "run-saju-1", sessionKey: "session-saju-1" };
await hooks.get("before_prompt_build")(
  { prompt: "오늘 사주 운세 알려줘", messages: [], runId: "run-saju-1" },
  context,
);
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
assert.equal(
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
