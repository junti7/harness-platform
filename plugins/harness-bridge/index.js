// Harness Bridge — OpenClaw plugin entry point
import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const SAJU_MARKERS = /사주|명리|일진|운세|십신|원국/;
const SAJU_FOLLOWUP_MARKERS =
  /시간대|좋은 시간|피할 시간|계속|이어서|더 자세히|그럼|같은 기준/;
const SAJU_NOTEBOOK_MARKERS =
  /d3fe3696-ff81-4810-94a8-9584c329c440|사주명리학자료/;
const WORKSPACE_STATS_INTENT =
  /(?:전체|폴더|디렉터리|directory|folder|disk).{0,20}(?:용량|크기|파일\s*(?:수|개수)|size|usage|count)|(?:용량|크기|size|usage).{0,20}(?:프로젝트|폴더|디렉터리|project|folder|directory)/i;
const HARNESS_WORKSPACE_MARKERS =
  /harness(?:-project|-platform)?|하네스|프로젝트\s*(?:폴더|디렉터리|저장소)|project\s+(?:folder|directory|repository)/i;
const MAX_TOOL_OUTPUT = 1_000_000;
const MAX_WRITE_BYTES = 2_000_000;
const READ_ONLY_GIT_SUBCOMMANDS = new Set([
  "branch",
  "diff",
  "log",
  "rev-parse",
  "show",
  "status",
]);

export function harnessRepoRoot() {
  return path.join(process.env.HOME ?? "", "projects", "harness-platform");
}

export function shouldEnforceWorkspaceStats(prompt) {
  const text = String(prompt ?? "");
  return WORKSPACE_STATS_INTENT.test(text) && HARNESS_WORKSPACE_MARKERS.test(text);
}

function humanBytes(bytes) {
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let value = Number(bytes) || 0;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
}

export async function collectHarnessWorkspaceStats(relativePath = ".") {
  const startedAt = Date.now();
  const target = resolveHarnessPath(relativePath, { mustExist: true });
  const stack = [target];
  let files = 0;
  let directories = 0;
  let symlinks = 0;
  let logicalBytes = 0;
  let unreadableEntries = 0;
  while (stack.length) {
    const current = stack.pop();
    let stat;
    try {
      stat = fs.lstatSync(current);
    } catch {
      unreadableEntries += 1;
      continue;
    }
    if (stat.isSymbolicLink()) {
      symlinks += 1;
      continue;
    }
    if (stat.isDirectory()) {
      directories += 1;
      try {
        for (const entry of fs.readdirSync(current)) stack.push(path.join(current, entry));
      } catch {
        unreadableEntries += 1;
      }
      continue;
    }
    if (stat.isFile()) {
      files += 1;
      logicalBytes += stat.size;
    }
  }
  const du = await runProcess("/usr/bin/du", ["-sk", target], { timeoutMs: 30_000 });
  if (du.code !== 0) throw new Error(`workspace_du_failed:${du.stderr.slice(0, 200)}`);
  const allocatedKiB = Number.parseInt(du.stdout.trim().split(/\s+/, 1)[0], 10);
  if (!Number.isFinite(allocatedKiB)) throw new Error("workspace_du_invalid_output");
  const allocatedBytes = allocatedKiB * 1024;
  return {
    path: path.relative(harnessRepoRoot(), target) || ".",
    allocatedBytes,
    allocatedHuman: humanBytes(allocatedBytes),
    logicalFileBytes: logicalBytes,
    logicalFileHuman: humanBytes(logicalBytes),
    files,
    directories,
    symlinks,
    unreadableEntries,
    durationMs: Date.now() - startedAt,
    semantics: {
      allocatedBytes: "Filesystem blocks used, equivalent to du -sk.",
      logicalFileBytes: "Sum of regular-file byte lengths; symlink targets are not followed.",
    },
  };
}

export function resolveHarnessPath(relativePath = ".", { mustExist = false } = {}) {
  const repo = fs.realpathSync(harnessRepoRoot());
  const candidate = path.resolve(repo, String(relativePath || "."));
  if (candidate !== repo && !candidate.startsWith(`${repo}${path.sep}`)) {
    throw new Error("path_outside_harness_workspace");
  }
  if (mustExist) {
    const real = fs.realpathSync(candidate);
    if (real !== repo && !real.startsWith(`${repo}${path.sep}`)) {
      throw new Error("symlink_outside_harness_workspace");
    }
    return real;
  }
  let existingParent = fs.existsSync(candidate) ? candidate : path.dirname(candidate);
  while (!fs.existsSync(existingParent) && existingParent !== path.dirname(existingParent)) {
    existingParent = path.dirname(existingParent);
  }
  const realParent = fs.realpathSync(existingParent);
  if (realParent !== repo && !realParent.startsWith(`${repo}${path.sep}`)) {
    throw new Error("symlink_outside_harness_workspace");
  }
  return candidate;
}

export function validateWorkspaceCommand(argv) {
  if (!Array.isArray(argv) || argv.length === 0 || argv.length > 64) {
    throw new Error("invalid_argv");
  }
  const parts = argv.map((value) => String(value));
  const executable = path.basename(parts[0]).toLowerCase();
  if (executable === "git") {
    if (parts[0] !== "git" && fs.realpathSync(parts[0]) !== fs.realpathSync("/usr/bin/git")) {
      throw new Error("untrusted_executable_path");
    }
    if (!READ_ONLY_GIT_SUBCOMMANDS.has(parts[1]) || parts.includes("-c")) {
      throw new Error("command_not_in_safe_verification_allowlist");
    }
    parts[0] = "/usr/bin/git";
    return parts;
  }
  if (executable === "node") {
    if (parts[0] !== "node" && fs.realpathSync(parts[0]) !== fs.realpathSync(process.execPath)) {
      throw new Error("untrusted_executable_path");
    }
    if (
      parts.length < 2 ||
      parts.slice(1).some((arg) => ["-e", "--eval", "-p", "--print", "-r", "--require", "--import"].includes(arg))
    ) {
      throw new Error("command_not_in_safe_verification_allowlist");
    }
    const script = resolveHarnessPath(parts[1], { mustExist: true });
    const relative = path.relative(harnessRepoRoot(), script);
    if (!relative.startsWith(`tests${path.sep}`) || !relative.endsWith(".mjs")) {
      throw new Error("command_not_in_safe_verification_allowlist");
    }
    parts[0] = process.execPath;
    parts[1] = script;
    return parts;
  }
  if (/^(?:python\d*(?:\.\d+)?)?-?pytest$/.test(executable) || executable === "pytest") {
    const trustedPytest = fs.realpathSync(path.join(harnessRepoRoot(), ".venv", "bin", "pytest"));
    if (parts[0] !== "pytest" && fs.realpathSync(parts[0]) !== trustedPytest) {
      throw new Error("untrusted_executable_path");
    }
    for (const arg of parts.slice(1)) {
      if (arg.startsWith("-")) continue;
      const selector = arg.split("::", 1)[0];
      const target = resolveHarnessPath(selector, { mustExist: true });
      const relative = path.relative(harnessRepoRoot(), target);
      if (!relative.startsWith(`tests${path.sep}`) && relative !== "tests") {
        throw new Error("command_not_in_safe_verification_allowlist");
      }
    }
    parts[0] = trustedPytest;
    return parts;
  }
  throw new Error("command_not_in_safe_verification_allowlist");
}

export function runProcess(executable, args, options = {}) {
  const timeoutMs = Math.min(Math.max(Number(options.timeoutMs) || 30_000, 1_000), 900_000);
  return new Promise((resolve, reject) => {
    const child = spawn(executable, args, {
      cwd: options.cwd ?? harnessRepoRoot(),
      env: process.env,
      stdio: ["pipe", "pipe", "pipe"],
    });
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
      finish(() => reject(new Error("command_timed_out")));
    }, timeoutMs);
    const collect = (field) => (chunk) => {
      if (field === "stdout") stdout += String(chunk);
      else stderr += String(chunk);
      if (stdout.length + stderr.length > MAX_TOOL_OUTPUT) {
        child.kill("SIGTERM");
        finish(() => reject(new Error("command_output_limit_exceeded")));
      }
    };
    child.stdout.on("data", collect("stdout"));
    child.stderr.on("data", collect("stderr"));
    child.on("error", (error) => finish(() => reject(error)));
    child.on("close", (code, signal) =>
      finish(() => resolve({ code, signal, stdout, stderr })),
    );
    if (options.stdin !== undefined) child.stdin.end(String(options.stdin));
    else child.stdin.end();
  });
}

function toolText(value, isError = false) {
  return {
    content: [{ type: "text", text: typeof value === "string" ? value : JSON.stringify(value) }],
    ...(isError ? { isError: true } : {}),
  };
}

function registerHarnessWorkspaceTools(api) {
  api.registerTool({
    name: "harness_workspace_stats",
    description: "Return fast, exact Harness repository disk usage, logical file bytes, and file/directory counts. Use for every Harness folder size, capacity, disk-usage, or file-count question; never search the home directory with shell/find.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        path: { type: "string", default: ".", description: "Path relative to the Harness repository root." },
      },
    },
    async execute(_id, params) {
      try {
        return toolText(await collectHarnessWorkspaceStats(params.path ?? "."));
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  });
  api.registerTool({
    name: "harness_workspace_read",
    description: "Read a UTF-8 file inside the Harness repository with line numbers.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: ["path"],
      properties: {
        path: { type: "string", minLength: 1 },
        startLine: { type: "integer", minimum: 1, default: 1 },
        maxLines: { type: "integer", minimum: 1, maximum: 5000, default: 500 },
      },
    },
    async execute(_id, params) {
      try {
        const file = resolveHarnessPath(params.path, { mustExist: true });
        const lines = fs.readFileSync(file, "utf8").split("\n");
        const start = (params.startLine ?? 1) - 1;
        const end = Math.min(lines.length, start + (params.maxLines ?? 500));
        return toolText({
          path: path.relative(harnessRepoRoot(), file),
          startLine: start + 1,
          endLine: end,
          totalLines: lines.length,
          content: lines.slice(start, end).map((line, index) => `${start + index + 1}: ${line}`).join("\n"),
        });
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  });
  api.registerTool({
    name: "harness_workspace_search",
    description: "Search Harness repository files using ripgrep. Returns matching file, line, and text.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: ["query"],
      properties: {
        query: { type: "string", minLength: 1, maxLength: 500 },
        path: { type: "string", default: "." },
        maxResults: { type: "integer", minimum: 1, maximum: 1000, default: 200 },
      },
    },
    async execute(_id, params) {
      try {
        const target = resolveHarnessPath(params.path ?? ".", { mustExist: true });
        const result = await runProcess(
          "rg",
          ["--line-number", "--color", "never", "--max-count", String(params.maxResults ?? 200), "--", params.query, target],
          { timeoutMs: 30_000 },
        );
        return toolText({ code: result.code, matches: result.stdout, errors: result.stderr });
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  });
  api.registerTool({
    name: "harness_workspace_write",
    description: "Create or overwrite one UTF-8 file inside the Harness repository. Returns SHA-256 evidence.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: ["path", "content"],
      properties: {
        path: { type: "string", minLength: 1 },
        content: { type: "string" },
        expectedSha256: { type: "string", description: "Optional optimistic-lock hash of the current file." },
      },
    },
    async execute(_id, params) {
      try {
        if (Buffer.byteLength(params.content, "utf8") > MAX_WRITE_BYTES) {
          throw new Error("write_size_limit_exceeded");
        }
        const file = resolveHarnessPath(params.path);
        if (params.expectedSha256) {
          if (!fs.existsSync(file)) throw new Error("optimistic_lock_target_missing");
          const current = crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
          if (current !== params.expectedSha256) throw new Error("optimistic_lock_conflict");
        }
        fs.mkdirSync(path.dirname(file), { recursive: true });
        const temp = `${file}.openclaw-${process.pid}-${Date.now()}.tmp`;
        fs.writeFileSync(temp, params.content, { encoding: "utf8", flag: "wx" });
        fs.renameSync(temp, file);
        const sha256 = crypto.createHash("sha256").update(params.content).digest("hex");
        return toolText({ ok: true, path: path.relative(harnessRepoRoot(), file), bytes: Buffer.byteLength(params.content), sha256 });
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  });
  api.registerTool({
    name: "harness_workspace_exec",
    description: "Run allowlisted Harness verification commands: read-only git operations and repository tests. Uses argv, never a shell string.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: ["argv"],
      properties: {
        argv: { type: "array", minItems: 1, maxItems: 64, items: { type: "string" } },
        cwd: { type: "string", default: "." },
        timeoutSeconds: { type: "integer", minimum: 1, maximum: 900, default: 30 },
      },
    },
    async execute(_id, params) {
      try {
        const argv = validateWorkspaceCommand(params.argv);
        const cwd = resolveHarnessPath(params.cwd ?? ".", { mustExist: true });
        const result = await runProcess(argv[0], argv.slice(1), {
          cwd,
          timeoutMs: (params.timeoutSeconds ?? 30) * 1000,
        });
        return toolText(result, result.code !== 0);
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  });
}

function registerHarnessAssistantTools(api) {
  const python = () => path.join(harnessRepoRoot(), ".venv", "bin", "python");
  const bridge = () => path.join(harnessRepoRoot(), "scripts", "openclaw_codex_bridge.py");
  const bridgeTool = (name, description, buildArgs, parameters) =>
    api.registerTool({
      name,
      description,
      parameters,
      async execute(_id, params) {
        try {
          const result = await runProcess(python(), [bridge(), ...buildArgs(params)], { timeoutMs: 180_000 });
          if (result.code !== 0) return toolText(result, true);
          return toolText(result.stdout);
        } catch (error) {
          return toolText({ ok: false, error: error.message }, true);
        }
      },
    });
  bridgeTool(
    "harness_gmail_search",
    "Search the CEO Gmail inbox read-only. Use before summarizing messages.",
    (p) => ["gmail-search", p.query, "--limit", String(p.limit ?? 10)],
    {
      type: "object", additionalProperties: false, required: ["query"],
      properties: { query: { type: "string", minLength: 1 }, limit: { type: "integer", minimum: 1, maximum: 100, default: 10 } },
    },
  );
  bridgeTool(
    "harness_gmail_get",
    "Retrieve one Gmail message body read-only by message ID.",
    (p) => ["gmail-get", p.messageId],
    {
      type: "object", additionalProperties: false, required: ["messageId"],
      properties: { messageId: { type: "string", minLength: 1 } },
    },
  );
  bridgeTool(
    "harness_calendar_list",
    "List Google Calendar events in a time range.",
    (p) => ["calendar-list", "--from-time", p.fromTime ?? "today", "--to-time", p.toTime ?? "", "--limit", String(p.limit ?? 10)],
    {
      type: "object", additionalProperties: false,
      properties: {
        fromTime: { type: "string", default: "today" },
        toTime: { type: "string", default: "" },
        limit: { type: "integer", minimum: 1, maximum: 100, default: 10 },
      },
    },
  );
  bridgeTool(
    "harness_calendar_create",
    "Create a Google Calendar event. Return the real event ID; never claim success without it.",
    (p) => [
      "calendar-create", p.summary, p.fromTime, p.toTime,
      "--description", p.description ?? "", "--location", p.location ?? "",
    ],
    {
      type: "object", additionalProperties: false, required: ["summary", "fromTime", "toTime"],
      properties: {
        summary: { type: "string", minLength: 1 },
        fromTime: { type: "string", minLength: 1, description: "ISO8601 with timezone offset" },
        toTime: { type: "string", minLength: 1, description: "ISO8601 with timezone offset" },
        description: { type: "string", default: "" },
        location: { type: "string", default: "" },
      },
    },
  );
  api.registerTool({
    name: "harness_cron_list",
    description: "List the real OpenClaw cron jobs and their IDs.",
    parameters: { type: "object", additionalProperties: false, properties: {} },
    async execute() {
      try {
        const result = await runProcess("/opt/homebrew/bin/openclaw", ["cron", "list", "--json"]);
        return toolText(result.stdout, result.code !== 0);
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  });
  api.registerTool({
    name: "harness_cron_create",
    description: "Create an OpenClaw recurring assistant job. Return the real cron job ID; never claim success without it.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: ["name", "cron", "message"],
      properties: {
        name: { type: "string", minLength: 1, maxLength: 120 },
        cron: { type: "string", minLength: 1, maxLength: 120, description: "5-field cron expression" },
        timezone: { type: "string", default: "Asia/Seoul" },
        message: { type: "string", minLength: 1, maxLength: 8000 },
        announce: { type: "boolean", default: true },
        channel: { type: "string", default: "last" },
        destination: { type: "string", description: "Optional Discord channel/user or other supported destination." },
      },
    },
    async execute(_id, params) {
      try {
        const args = [
          "cron", "add", "--json", "--name", params.name,
          "--cron", params.cron, "--tz", params.timezone ?? "Asia/Seoul",
          "--agent", "main", "--session", "isolated",
          "--message", params.message, "--timeout-seconds", "300",
          "--channel", params.channel ?? "last",
          params.announce === false ? "--no-deliver" : "--announce",
        ];
        if (params.destination) args.push("--to", params.destination);
        const result = await runProcess("/opt/homebrew/bin/openclaw", args);
        return toolText(result.stdout || result.stderr, result.code !== 0);
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  });
  api.registerTool({
    name: "harness_cron_remove",
    description: "Remove one OpenClaw cron job by exact ID after the user explicitly requests cancellation.",
    parameters: {
      type: "object", additionalProperties: false, required: ["jobId"],
      properties: { jobId: { type: "string", minLength: 1 } },
    },
    async execute(_id, params) {
      try {
        const result = await runProcess("/opt/homebrew/bin/openclaw", ["cron", "remove", params.jobId, "--json"]);
        return toolText(result.stdout || result.stderr, result.code !== 0);
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  });
}

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
    registerHarnessWorkspaceTools(api);
    registerHarnessAssistantTools(api);
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
        if (shouldEnforceWorkspaceStats(event.prompt)) {
          return {
            appendSystemContext: [
              "[HARNESS WORKSPACE STATS — MANDATORY]",
              "For Harness repository size, disk usage, file count, or directory count questions,",
              "call only `harness_workspace_stats` with a repository-relative path.",
              "Treat harness-project as an alias for the configured harness-platform root.",
              "Never use bash, find, du, or a home-directory scan for this intent.",
              "Answer directly from allocatedHuman/logicalFileHuman and counts.",
            ].join(" "),
          };
        }
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
