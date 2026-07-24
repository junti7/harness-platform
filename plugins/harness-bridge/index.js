// Harness Bridge — OpenClaw plugin entry point
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const SAJU_MARKERS = /사주|명리|일진|운세|십신|원국/;
const SAJU_FOLLOWUP_MARKERS =
  /시간대|좋은 시간|피할 시간|계속|이어서|더 자세히|그럼|같은 기준/;
const SAJU_NOTEBOOK_MARKERS =
  /d3fe3696-ff81-4810-94a8-9584c329c440|사주명리학자료/;

export function shouldEnforceSajuBridge(prompt, messages = []) {
  if (SAJU_MARKERS.test(String(prompt ?? ""))) {
    return true;
  }
  if (!SAJU_FOLLOWUP_MARKERS.test(String(prompt ?? ""))) {
    return false;
  }
  return messages.some((message) => {
    try {
      return SAJU_MARKERS.test(JSON.stringify(message?.content ?? ""));
    } catch {
      // A contextual follow-up with malformed history must not lose the safe route.
      return true;
    }
  });
}

export function isDirectSajuNotebookQuery(toolName, params = {}, activeSajuRun = false) {
  let serialized;
  try {
    serialized = JSON.stringify(params);
  } catch {
    // Fail closed only for query-capable tools; unrelated tools remain unaffected.
    return /bash|exec|notebooklm[\s\S]*(?:query|chat)/i.test(String(toolName));
  }
  if (activeSajuRun && isShellTool(toolName) && /\bnlm\b/i.test(serialized)) {
    return true;
  }
  if (isShellTool(toolName) && /\bnlm\b/i.test(serialized) && SAJU_NOTEBOOK_MARKERS.test(serialized)) {
    // Block direct calls to the fixed Saju notebook without disrupting
    // unrelated NotebookLM operator diagnostics.
    return true;
  }
  const directNotebookLmTool =
    /notebooklm[\s\S]*(?:query|chat)/i.test(String(toolName));
  return directNotebookLmTool && (activeSajuRun || SAJU_NOTEBOOK_MARKERS.test(serialized));
}

export function isShellTool(toolName) {
  return /bash|exec|shell|terminal|command/i.test(String(toolName));
}

export function runSajuBridge(question, timeoutMs = 300_000) {
  return new Promise((resolve, reject) => {
    const repo = path.join(process.env.HOME ?? "", "projects", "harness-platform");
    const trustedRepo =
      [
        ".git",
        ".venv/bin/python",
        "core/saju_calendar.py",
        "scripts/openclaw_codex_bridge.py",
      ].every((required) => fs.existsSync(path.join(repo, required)));
    if (!trustedRepo) {
      reject(new Error("Harness repository root was not found"));
      return;
    }
    const child = spawn(
      path.join(repo, ".venv", "bin", "python"),
      [
        path.join(repo, "scripts", "openclaw_codex_bridge.py"),
        "saju-notebook-query",
        "--question-stdin",
        "--format",
        "relay",
        "--timeout",
        "300",
      ],
      {
        cwd: repo,
        env: process.env,
        stdio: ["pipe", "pipe", "pipe"],
      },
    );
    let stdout = "";
    let stderr = "";
    let settled = false;
    const finish = (callback) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      callback();
    };
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      setTimeout(() => child.kill("SIGKILL"), 2_000).unref();
      finish(() => reject(new Error("Saju bridge timed out")));
    }, timeoutMs);
    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
      if (stdout.length > 2_000_000) {
        child.kill("SIGTERM");
        setTimeout(() => child.kill("SIGKILL"), 2_000).unref();
        finish(() => reject(new Error("Saju bridge output exceeded safety limit")));
      }
    });
    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });
    child.on("error", (error) => {
      finish(() => reject(error));
    });
    child.on("close", (code) => {
      if (code !== 0) {
        finish(() =>
          reject(new Error(`Saju bridge failed with exit code ${code}: ${stderr.slice(0, 300)}`)),
        );
        return;
      }
      finish(() => resolve(stdout));
    });
    child.stdin.end(String(question));
  });
}

export default {
  id: "harness-bridge",
  name: "Harness Bridge",
  description: "Harness OpenClaw command bundle for the Codex bridge",
  register(api) {
    const activeSajuRuns = new Map();
    const runKeys = (event = {}, context = {}) =>
      [event.runId, context.runId, context.sessionKey, context.sessionId]
        .filter(Boolean)
        .map(String);
    const pruneRuns = () => {
      const now = Date.now();
      for (const [key, expiresAt] of activeSajuRuns) {
        if (expiresAt <= now) activeSajuRuns.delete(key);
      }
      while (activeSajuRuns.size > 1024) {
        activeSajuRuns.delete(activeSajuRuns.keys().next().value);
      }
    };
    const markSajuRun = (event, context) => {
      pruneRuns();
      const expiresAt = Date.now() + 10 * 60_000;
      for (const key of runKeys(event, context)) activeSajuRuns.set(key, expiresAt);
    };
    const isSajuRun = (event, context) => {
      pruneRuns();
      return runKeys(event, context).some((key) => activeSajuRuns.has(key));
    };
    const clearSajuRun = (event, context) => {
      for (const key of runKeys(event, context)) activeSajuRuns.delete(key);
    };
    api.registerTool({
      name: "harness_saju_query",
      description:
        "Query the fixed Saju NotebookLM through deterministic dates, expert validation, private cache, and compact relay. Use for every Saju request and follow-up.",
      parameters: {
        type: "object",
        additionalProperties: false,
        required: ["question"],
        properties: {
          question: {
            type: "string",
            description:
              "Self-contained question with explicit birth date/time and target date reconstructed from conversation.",
            minLength: 1,
            maxLength: 4000,
          },
        },
      },
      async execute(_toolCallId, params) {
        try {
          const output = await runSajuBridge(params.question);
          return { content: [{ type: "text", text: output }] };
        } catch (error) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  ok: false,
                  error: "saju_bridge_failed",
                }),
              },
            ],
            isError: true,
          };
        }
      },
    });
    api.on(
      "before_prompt_build",
      async (event, context) => {
        if (!shouldEnforceSajuBridge(event.prompt, event.messages)) {
          return;
        }
        markSajuRun(event, context);
        return {
          appendSystemContext: [
            "[HARNESS SAJU ROUTING — MANDATORY]",
            "For any Saju/명리/일진/운세 request and its contextual follow-ups,",
            "NEVER run `nlm notebook query`, NotebookLM MCP query, or nlm-skill directly.",
            "Reconstruct omitted birth/target dates and birth time from recent conversation,",
            "then call only the `harness_saju_query` tool. Send delivery_text verbatim.",
            "The bridge owns deterministic dates, expert contracts, privacy, and cache.",
          ].join(" "),
        };
      },
      { priority: 1000 },
    );
    api.on(
      "before_tool_call",
      async (event, context) => {
        if (!isDirectSajuNotebookQuery(event.toolName, event.params, isSajuRun(event, context))) {
          return;
        }
        return {
          block: true,
          blockReason:
            "Direct Saju NotebookLM queries are blocked; use the privacy-safe cached Harness bridge.",
        };
      },
      { priority: 1000 },
    );
    api.on("agent_end", async (event, context) => {
      clearSajuRun(event, context);
    });
  },
};
