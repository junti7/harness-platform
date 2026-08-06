// Harness Bridge — OpenClaw plugin entry point
import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const SAJU_MARKERS = /사주|명리|일진|운세|십신|원국/;
const SAJU_FOLLOWUP_MARKERS =
  /시간대|좋은 시간|피할 시간|계속|이어서|더 자세히|그럼|같은 기준/;
const SAJU_NOTEBOOK_MARKERS =
  /d3fe3696-ff81-4810-94a8-9584c329c440|사주명리학자료/;
const SAJU_NOTEBOOK_STATUS_INTENT =
  /(?:(?:노트북|notebook|NotebookLM).{0,80}(?:소스|source|추가|등록|업로드|목록|확인|잘\s*추가|들어갔|들어갔는지)|(?:자료|소스|source|리서치).{0,40}(?:추가|등록|업로드|목록|확인|잘\s*추가|들어갔|들어갔는지))/i;
const SAJU_NOTEBOOK_STATUS_EXCLUDED_INTENT =
  /(?:바탕으로|기준으로|참고해서|근거로).{0,40}(?:운세|총운|일진|해석|분석|알려|풀이)|(?:운세|총운|일진|해석|분석|풀이).{0,40}(?:알려|해줘|봐줘|해석|분석)/i;
const SAJU_NOTEBOOK_SEARCH_TERMS = [
  "대운",
  "월운",
  "세운",
  "일진",
  "격국",
  "용신",
  "상신",
  "십신",
  "신살",
  "원국",
  "사주명리학",
  "명리학",
];
const WORKSPACE_STATS_INTENT =
  /(?:전체|폴더|디렉터리|directory|folder|disk).{0,20}(?:용량|크기|파일\s*(?:수|개수)|size|usage|count)|(?:용량|크기|size|usage).{0,20}(?:프로젝트|폴더|디렉터리|project|folder|directory)/i;
const HARNESS_WORKSPACE_MARKERS =
  /harness(?:-project|-platform)?|하네스|프로젝트\s*(?:폴더|디렉터리|저장소)|project\s+(?:folder|directory|repository)/i;
const HARNESS_KNOWLEDGE_MARKERS =
  /harness|하네스|turtle|터틀|trading|트레이딩|alpaca|ibkr|자료\s*수입|교육\s*사업|교육|ojt|스마트팜|smartfarm|physical\s*ai\s*weekly|구독\s*사업|pretotyping|openclaw/i;
const HARNESS_HARDWARE_MODEL_MARKERS =
  /\besp\d+\b|\bnodemcu\b|\bdht\d+\b|\braspberry\s*pi\b|라즈베리\s*파이/i;
const HARNESS_HARDWARE_INTENT_MARKERS =
  /연결|배선|핀|센서|릴레이|펌프|보드|펌웨어|\b(?:gpio|sensor|relay|pump|board|firmware)\b/i;
const SMARTFARM_PUMP_CONTEXT =
  /farm\/zone[1-9][0-9]{0,2}\/pump\/cmd|펌프|릴레이|\bpump\b/i;
const COPILOT_USAGE_CONTEXT =
  /(?:github\s*)?copilot|코파일럿/i;
const COPILOT_USAGE_INTENT =
  /premium\s*request|billing|budget|charge|cost|usage|request|과금|결제|비용|예산|사용량|요청|세션|모델|원인/i;
const NOTION_ARCHIVE_REQUEST =
  /(?:notion|노션)(?:에|으로|에다가|\s){0,6}.{0,40}(?:기록|저장|등록|아카이브|다시\s*실행|재실행|archive|save|record|create|retry|run\s+again)/i;
const BROWSER_OPEN_REQUEST =
  /(?:(?:browser|브라우저|chrome|크롬).{0,40}(?:띄워|열어|켜|접속|open|launch|go\s*to)|(?:쿠팡|coupang).{0,40}(?:접속|열어|띄워|open|launch))/i;
const COUPANG_SEARCH_REQUEST =
  /(?:쿠팡|coupang).{0,40}(?:검색|찾아|찾기|search).{0,80}(?:상품|제품|결과|보여|알려|수집|collect|product|item)|(?:쿠팡|coupang).{0,20}(?:에서|에)?\s*.{1,60}(?:검색|찾아|찾기|search)/i;
const COUPANG_PRODUCT_EVIDENCE_REQUEST =
  /(?:쿠팡|coupang).{0,100}(?:가격|최저가|판매가|얼마|상품|제품).{0,40}(?:알아|알려|확인|찾아|검색|보여|봐|check|find|price)|(?:쿠팡|coupang).{0,40}(?:띄워|열어|접속).{0,100}(?:가격|최저가|판매가|얼마)/i;
const COUPANG_DETAIL_OPEN_REQUEST =
  /(?:(?:쿠팡|coupang).{0,80})?(?:(?:상품|제품).{0,30}(?:들어가|열어|상세)|(?:들어가|열어).{0,30}(?:상품|제품|상세)|[0-9]{1,3}(?:,[0-9]{3})+\s*원\s*짜리.{0,40}(?:들어가|열어|상세))/i;
const SCREEN_INSPECT_REQUEST =
  /(?:(?:지금|현재|떠\s*있는|열려\s*있는|보이는).{0,50}(?:화면|창|브라우저|browser|chrome|크롬|쿠팡|coupang).{0,50}(?:보여|보이는|뭐|무엇|어떤|확인|읽어|describe|see|visible)|(?:화면|창|screen|window).{0,50}(?:보여|보이는|뭐|무엇|어떤|확인|읽어|describe|see|visible))/i;
const SCREEN_INSPECT_FOLLOWUP_REQUEST =
  /^(?:다시\s*)?(?:확인|재확인|봐줘|읽어줘|해봐|retry|again)(?:해|해줘|해봐|해줘요|요)?[.!?\s]*$/i;
const SCREEN_INSPECT_DETAIL_FOLLOWUP_REQUEST =
  /(?:(?:어떤|무슨|뭐|무엇).{0,20}(?:제품|상품|메뉴|배너|목록|item|product).{0,20}(?:보여|보이는|있어|나와|읽어|확인|visible|see)|(?:제품|상품|메뉴|배너|목록|item|product).{0,30}(?:보여|보이는|읽어|확인|visible|see))/i;
const SCREEN_INSPECT_CONTEXT_MARKERS =
  /harness_screen_inspect|peekaboo_permissions_not_granted|peekaboo_bridge_socket_missing|peekaboo_bridge_not_ready|Screen Recording|Accessibility|화면\s*(?:판독|검사|내용\s*읽기|브리지|읽)/i;
const HIGH_IMPACT_BROWSER_ACTION =
  /구매|결제|주문|checkout|buy|pay|order|(?:장바구니|cart).{0,20}(?:담아|넣어|추가|add)|(?:담아|넣어|추가|add).{0,20}(?:장바구니|cart)|로그인(?:을|를)?\s*(?:해|해줘|하라|진행|시도)|(?:login|log\s*in)\s*(?:do|attempt|submit|now)/i;
const HIGH_IMPACT_BROWSER_BRIDGE_COMMAND =
  /\b(?:browser-fill|coupang-setup|coupang-cart|coupang-pay-approve)\b/i;
const CEO_VERIFICATION_REQUEST =
  /(?:(?:직접\s*)?(?:확인|조회|검증|점검)(?:해|해서|하고|하라|해주세요|해줘|해봐|해보|해라)|알아봐(?:\s*(?:줘|라|세요|주세요|해줘))?[.!?\s]*$|(?:근거|증빙).{0,30}(?:제공|보여|보내|첨부|확인))/i;
let pluginOwnerSenderIds = new Set();
let pluginOwnerSessionKeys = new Set();
const browserOpenExecutionTokens = new Map();
const screenInspectExecutionTokens = new Map();
const coupangDetailOpenExecutionTokens = new Map();
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

export function shouldEnforceHarnessKnowledge(prompt) {
  const text = String(prompt ?? "");
  return (
    HARNESS_KNOWLEDGE_MARKERS.test(text) ||
    (HARNESS_HARDWARE_MODEL_MARKERS.test(text) && HARNESS_HARDWARE_INTENT_MARKERS.test(text))
  );
}

export function shouldEnforceCopilotUsage(prompt) {
  const raw = String(prompt ?? "");
  const currentRequestMarker = "Current user request:";
  const markerIndex = raw.lastIndexOf(currentRequestMarker);
  const text =
    markerIndex >= 0
      ? raw.slice(markerIndex + currentRequestMarker.length)
      : raw.replace(/<conversation_context>[\s\S]*?<\/conversation_context>/gi, "");
  return COPILOT_USAGE_CONTEXT.test(text) && COPILOT_USAGE_INTENT.test(text);
}

export function shouldEnforceBrowserOpen(prompt) {
  const text = currentUserInstruction(prompt);
  return (
    BROWSER_OPEN_REQUEST.test(text) ||
    COUPANG_SEARCH_REQUEST.test(text) ||
    COUPANG_PRODUCT_EVIDENCE_REQUEST.test(text)
  ) && !HIGH_IMPACT_BROWSER_ACTION.test(text);
}

export function shouldEnforceVerificationEvidence(prompt) {
  return CEO_VERIFICATION_REQUEST.test(currentUserInstruction(prompt));
}

export function shouldEnforceScreenInspect(prompt, messages = [], context = {}) {
  const text = currentUserInstruction(prompt);
  if (
    (COUPANG_SEARCH_REQUEST.test(text) || COUPANG_PRODUCT_EVIDENCE_REQUEST.test(text)) &&
    !HIGH_IMPACT_BROWSER_ACTION.test(text)
  ) {
    return true;
  }
  if (SCREEN_INSPECT_REQUEST.test(text) && !HIGH_IMPACT_BROWSER_ACTION.test(text)) {
    return true;
  }
  if (SCREEN_INSPECT_DETAIL_FOLLOWUP_REQUEST.test(text) && !HIGH_IMPACT_BROWSER_ACTION.test(text)) {
    return trustedScreenInspectContext(prompt, messages).some((contextText) =>
      SCREEN_INSPECT_CONTEXT_MARKERS.test(contextText),
    ) || hasRecentScreenInspectTrajectory(context);
  }
  if (!SCREEN_INSPECT_FOLLOWUP_REQUEST.test(text) || HIGH_IMPACT_BROWSER_ACTION.test(text)) {
    return false;
  }
  return trustedScreenInspectContext(prompt, messages).some((contextText) =>
    SCREEN_INSPECT_CONTEXT_MARKERS.test(contextText),
  ) || hasRecentScreenInspectTrajectory(context);
}

function trustedScreenInspectContext(prompt, messages = []) {
  const trusted = [];
  void prompt;
  for (const message of messages) {
    const role = String(message?.role ?? "").toLowerCase();
    const toolName = String(message?.toolName ?? message?.name ?? "");
    if (role === "toolresult" && toolName === "harness_screen_inspect") {
      trusted.push(toolName);
      continue;
    }
    if (role !== "assistant") continue;
    const contentItems = Array.isArray(message?.content) ? message.content : [];
    if (
      contentItems.some(
        (item) =>
          item &&
          typeof item === "object" &&
          String(item.type ?? "") === "toolCall" &&
          String(item.name ?? item.toolName ?? "") === "harness_screen_inspect",
      )
    ) {
      trusted.push("harness_screen_inspect");
    }
  }
  return trusted;
}

function hasRecentScreenInspectTrajectory(context = {}) {
  const sessionId = String(context.sessionId ?? "");
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(sessionId)) {
    return false;
  }
  const baseDir =
    process.env.OPENCLAW_TRAJECTORY_DIR ||
    path.join(os.homedir(), ".openclaw", "agents", "main", "sessions");
  const resolvedBaseDir = path.resolve(baseDir);
  const trajectoryPath = path.resolve(resolvedBaseDir, `${sessionId}.trajectory.jsonl`);
  if (!trajectoryPath.startsWith(`${resolvedBaseDir}${path.sep}`)) return false;
  let fd;
  try {
    fd = fs.openSync(trajectoryPath, "r");
    const stats = fs.fstatSync(fd);
    const maxBytes = 1_000_000;
    const start = Math.max(0, stats.size - maxBytes);
    const buffer = Buffer.alloc(stats.size - start);
    const bytesRead = fs.readSync(fd, buffer, 0, buffer.length, start);
    if (bytesRead !== buffer.length) return false;
    let text = buffer.toString("utf8");
    if (start > 0) {
      const firstNewline = text.indexOf("\n");
      if (firstNewline < 0) return false;
      text = text.slice(firstNewline + 1);
    }
    const events = text
      .split(/\r?\n/)
      .filter(Boolean)
      .slice(-80)
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch {
          return undefined;
        }
      })
      .filter(Boolean);
    const sawToolCall = events.some(
      (event) => event?.type === "tool.call" && event?.data?.name === "harness_screen_inspect",
    );
    const sawToolResult = events.some(
      (event) =>
        event?.type === "tool.result" &&
        event?.data?.name === "harness_screen_inspect" &&
        screenInspectTrajectoryResultMatches(event.data),
    );
    return sawToolCall && sawToolResult;
  } catch {
    return false;
  } finally {
    if (fd !== undefined) {
      try {
        fs.closeSync(fd);
      } catch {}
    }
  }
}

function screenInspectTrajectoryResultMatches(data = {}) {
  const items = Array.isArray(data.contentItems) ? data.contentItems : [];
  return items.some((item) => {
    if (!item || typeof item !== "object") return false;
    const text = String(item.text ?? item.content ?? "");
    try {
      const parsed = JSON.parse(text);
      return (
        parsed?.ok === true ||
        [
          "peekaboo_permissions_not_granted",
          "peekaboo_bridge_socket_missing",
          "peekaboo_bridge_not_ready",
        ].includes(String(parsed?.error ?? ""))
      );
    } catch {
      return false;
    }
  });
}

export function selectBestPeekabooWindow(windows = [], preferredPattern) {
  const validWindows = [...windows].filter(
    (window) => window && window.is_on_screen !== false && Number(window.window_id) > 0,
  );
  const preferredWindows = preferredPattern
    ? validWindows.filter((window) =>
        preferredPattern.test(
          [
            window.window_title,
            window.title,
            window.url,
            window.app,
            window.application_name,
          ]
            .filter(Boolean)
            .join(" "),
        ),
      )
    : [];
  return (preferredWindows.length ? preferredWindows : validWindows)
    .sort((left, right) => {
      const leftBounds = left.bounds ?? {};
      const rightBounds = right.bounds ?? {};
      const leftArea = Number(leftBounds.width ?? 0) * Number(leftBounds.height ?? 0);
      const rightArea = Number(rightBounds.width ?? 0) * Number(rightBounds.height ?? 0);
      return rightArea - leftArea;
    })[0];
}

export {
  normalizeProductText,
  productSearchTermsFromQuestion,
  productSearchTermsFromCoupangWindowTitle,
  productCardCandidatesFromOcr,
  deterministicCoupangEvidenceReply,
  composeEvidenceReplyText,
  disposablePeekabooCapturePaths,
  verificationEvidenceToolRelevant,
};

function compactPeekabooSeeResult(parsed) {
  const data = parsed?.data ?? parsed;
  const elements = Array.isArray(data?.ui_elements) ? data.ui_elements : [];
  return {
    success: Boolean(parsed?.success ?? data?.success),
    application_name: data?.application_name,
    window_title: data?.window_title,
    capture_mode: data?.capture_mode,
    element_count: data?.element_count,
    screenshot_raw: data?.screenshot_raw,
    ui_map: data?.ui_map,
    visible_elements: elements
      .filter((element) => {
        const text = String(element?.label ?? element?.title ?? element?.description ?? "").trim();
        return text && text !== "그룹";
      })
      .slice(0, 25)
      .map((element) => ({
        role: element.role_description ?? element.role,
        label: element.label,
        title: element.title,
        description: element.description,
        actionable: Boolean(element.is_actionable),
      })),
  };
}

async function runMacVisionOcr(imagePath) {
  const resolved = path.resolve(String(imagePath ?? ""));
  if (!resolved || !fs.existsSync(resolved)) {
    return { ok: false, error: "ocr_image_missing" };
  }
  const allowedImageRoots = [
    path.resolve(os.tmpdir()),
    path.resolve(path.join(os.homedir(), "Desktop")),
    path.resolve(path.join(os.homedir(), ".peekaboo")),
  ];
  if (!allowedImageRoots.some((root) => resolved === root || resolved.startsWith(`${root}${path.sep}`))) {
    return { ok: false, error: "ocr_image_path_not_allowed" };
  }
  const scriptPath = path.join(harnessRepoRoot(), "scripts", "macos_vision_ocr.swift");
  if (!fs.existsSync(scriptPath)) {
    return { ok: false, error: "ocr_script_missing" };
  }
  const binaryPath = path.join(harnessRepoRoot(), "scratch", "macos_vision_ocr");
  try {
    fs.mkdirSync(path.dirname(binaryPath), { recursive: true });
    const scriptStat = fs.statSync(scriptPath);
    const binaryStat = fs.existsSync(binaryPath) ? fs.statSync(binaryPath) : undefined;
    if (!binaryStat || binaryStat.mtimeMs < scriptStat.mtimeMs) {
      const compile = await runProcess("/usr/bin/swiftc", [scriptPath, "-O", "-o", binaryPath], {
        timeoutMs: 90_000,
      });
      if (compile.code !== 0) {
        return {
          ok: false,
          error: "ocr_compile_failed",
          detail: summarizePeekabooFailure(compile),
        };
      }
    }
  } catch (error) {
    return { ok: false, error: "ocr_compile_exception", detail: error.message };
  }
  try {
    const result = await runProcess(binaryPath, [resolved], { timeoutMs: 20_000 });
    if (result.code !== 0) {
      return {
        ok: false,
        error: "ocr_failed",
        detail: summarizePeekabooFailure(result),
      };
    }
    const parsed = JSON.parse(result.stdout);
    const lines = Array.isArray(parsed.lines) ? parsed.lines : [];
    const text = sanitizeCollectedText(parsed.text)
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(0, 80)
      .join("\n")
      .slice(0, 6_000);
    return {
      ok: parsed.ok === true,
      line_count: lines.length,
      lines: lines.slice(0, 80).map((line) => ({
        text: sanitizeCollectedText(line.text).slice(0, 200),
        confidence: Number(line.confidence ?? 0),
        bounding_box: Array.isArray(line.boundingBox)
          ? line.boundingBox.slice(0, 4).map((value) => Number(value))
          : undefined,
      })),
      text,
      error: parsed.error,
    };
  } catch (error) {
    return { ok: false, error: "ocr_exception", detail: error.message };
  }
}

function disposablePeekabooCapturePaths(result) {
  const candidates = [
    result?.result?.screenshot_raw,
    ...(result?.result?.smart_collection?.pages ?? []).map((page) => page?.screenshot_raw),
  ];
  const disposableRoots = [
    path.resolve(os.tmpdir()),
    path.resolve(path.join(os.homedir(), ".peekaboo")),
    path.resolve(path.join(os.homedir(), "Desktop")),
  ];
  return [...new Set(candidates.filter(Boolean).map((candidate) => path.resolve(String(candidate))))]
    .filter((candidate) => /^peekaboo_see_[0-9]+\.png$/i.test(path.basename(candidate)))
    .filter((candidate) => {
      try {
        const stat = fs.lstatSync(candidate);
        const ageMs = Date.now() - stat.mtimeMs;
        return (
          stat.isFile() &&
          !stat.isSymbolicLink() &&
          stat.nlink === 1 &&
          ageMs >= -10_000 &&
          ageMs <= 5 * 60_000
        );
      } catch {
        return false;
      }
    })
    .filter((candidate) =>
      disposableRoots.some(
        (root) => candidate === root || candidate.startsWith(`${root}${path.sep}`),
      ),
    )
    .slice(0, 4);
}

function moveDisposableCaptureToTrash(imagePath, expectedIdentity) {
  const resolved = path.resolve(String(imagePath ?? ""));
  const disposableRoots = [
    path.resolve(os.tmpdir()),
    path.resolve(path.join(os.homedir(), ".peekaboo")),
    path.resolve(path.join(os.homedir(), "Desktop")),
  ];
  if (
    !fs.existsSync(resolved) ||
    !disposableRoots.some(
      (root) => resolved === root || resolved.startsWith(`${root}${path.sep}`),
    )
  ) {
    return false;
  }
  if (!/^peekaboo_see_[0-9]+\.png$/i.test(path.basename(resolved))) return false;
  const currentStat = fs.lstatSync(resolved);
  if (!currentStat.isFile() || currentStat.isSymbolicLink() || currentStat.nlink !== 1) return false;
  if (
    expectedIdentity &&
    (currentStat.dev !== expectedIdentity.dev || currentStat.ino !== expectedIdentity.ino)
  ) {
    return false;
  }
  const trashDir = path.join(os.homedir(), ".Trash");
  fs.mkdirSync(trashDir, { recursive: true });
  const extension = path.extname(resolved).slice(0, 12);
  const target = path.join(
    trashDir,
    `OpenClaw-Peekaboo-${Date.now()}-${crypto.randomUUID()}${extension}`,
  );
  try {
    fs.renameSync(resolved, target);
  } catch (error) {
    if (error?.code === "EXDEV") {
      const sourceFd = fs.openSync(
        resolved,
        fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW ?? 0),
      );
      let targetFd;
      try {
        const sourceStat = fs.fstatSync(sourceFd);
        if (sourceStat.dev !== currentStat.dev || sourceStat.ino !== currentStat.ino) {
          return false;
        }
        targetFd = fs.openSync(
          target,
          fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL,
          0o600,
        );
        const buffer = Buffer.alloc(64 * 1024);
        let bytesRead;
        while ((bytesRead = fs.readSync(sourceFd, buffer, 0, buffer.length, null)) > 0) {
          let offset = 0;
          while (offset < bytesRead) {
            offset += fs.writeSync(targetFd, buffer, offset, bytesRead - offset);
          }
        }
        const finalPathStat = fs.lstatSync(resolved);
        if (
          finalPathStat.dev !== sourceStat.dev ||
          finalPathStat.ino !== sourceStat.ino ||
          finalPathStat.isSymbolicLink()
        ) {
          fs.unlinkSync(target);
          return false;
        }
        fs.unlinkSync(resolved);
      } finally {
        if (targetFd !== undefined) fs.closeSync(targetFd);
        fs.closeSync(sourceFd);
      }
      return true;
    }
    throw error;
  }
  return true;
}

function deterministicCoupangEvidenceReply(result) {
  if (!result?.ok) {
    const rawError = sanitizeCollectedText(result?.error || "");
    const safeError = /^[a-z0-9_:-]{1,120}$/i.test(rawError)
      ? rawError
      : "screen_inspection_failed";
    return `쿠팡 화면 판독 실패: ${safeError}. 화면에서 가격을 확인하지 못했습니다.`;
  }
  const matches = result?.result?.smart_collection?.merged?.strict_product_matches ?? [];
  if (!Array.isArray(matches) || matches.length === 0) {
    return "현재 쿠팡 화면 OCR에서 검색어가 같은 상품 카드 안에 모두 들어간 제품과 가격을 확인하지 못했습니다.";
  }
  const rows = [];
  const seen = new Set();
  for (const match of matches) {
    const title =
      (match.title_candidates ?? []).find((candidate) => sanitizeCollectedText(candidate)) ||
      (match.lines ?? []).find((candidate) => sanitizeCollectedText(candidate));
    const price = (match.current_price_candidates ?? [])[0];
    if (!title || !price) continue;
    const cleanTitle = sanitizeOutboundEvidenceText(title).slice(0, 240);
    const cleanPrice = sanitizeCollectedText(price).match(/[0-9]{1,3}(?:,[0-9]{3})*\s*원/)?.[0];
    if (!cleanPrice) continue;
    const key = `${normalizeProductText(cleanTitle)}:${normalizeProductText(cleanPrice)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push(`- ${cleanTitle}: ${cleanPrice}`);
  }
  if (rows.length === 0) {
    return "현재 쿠팡 화면 OCR에서 상품명과 같은 카드에 속한 현재 가격을 확정하지 못했습니다.";
  }
  return ["근거: 현재 쿠팡 화면 OCR", ...rows].join("\n");
}

function sanitizeOutboundEvidenceText(value) {
  return sanitizeCollectedText(value)
    .replace(/@/g, "@\u200b")
    .replace(/```/g, "'''")
    .replace(/[<>]/g, "")
    .replace(/([*_~\[\]])/g, "\\$1");
}

function composeEvidenceReplyText({ baseText, pendingText, evidenceText, verificationFailed }) {
  return verificationFailed
    ? [pendingText, evidenceText].filter(Boolean).join("\n\n")
    : [baseText, evidenceText].filter(Boolean).join("\n\n");
}

function sanitizeCollectedText(value) {
  return String(value ?? "")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeProductText(value) {
  return sanitizeCollectedText(value)
    .toLowerCase()
    .replace(/[\s"'`‘’“”()[\]{}<>·ㆍ•|/\\.,:;!?~_\-+*=]/g, "");
}

function productSearchTermsFromQuestion(question) {
  const text = currentUserInstruction(question);
  const query = coupangSearchQueryFromPrompt(text) ?? text;
  const cleaned = sanitizeCollectedText(query)
    .replace(/(?:쿠팡|coupang|에서|현재|가격|최저가|검색|찾아|찾기|search|제품|상품|결과|보여줘|알려줘|알려|수집|상세|정보|들어가서|들어가|짜리|원)/gi, " ")
    .replace(/(?:진입|열어|열기)/gi, " ")
    .replace(/[0-9]{1,3}(?:,[0-9]{3})+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return [
    ...new Set(
      cleaned
        .split(/\s+/)
        .map((term) => term.trim())
        .filter((term) => term.length >= 2)
        .filter((term) => !/^(?:을|를|이|가|은|는|좀|해줘|해|줘)$/.test(term)),
    ),
  ].slice(0, 6);
}

function productSearchTermsFromCoupangWindowTitle(title) {
  const text = sanitizeCollectedText(title);
  const match = text.match(/^쿠팡이\s*추천하는\s+(.{2,80}?)\s+관련\s*혜택과\s*특가(?:\s*-\s*Chrome)?$/i);
  if (!match) return [];
  const candidate = sanitizeCollectedText(match[1]);
  if (!candidate || /(?:https?:\/\/|www\.|coupang\.com|[<>{}[\]\\])/i.test(candidate)) return [];
  const terms = productSearchTermsFromQuestion(`쿠팡에서 ${candidate} 검색`).filter(
    (term) => !/^(?:추천|추천하는|관련|혜택|특가|쿠팡|chrome)$/i.test(term),
  );
  return terms.length >= 2 ? terms.slice(0, 4) : [];
}

function priceStringsFromText(text) {
  const values = [];
  const pattern = /(?:₩\s*)?([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,})\s*원/g;
  let match;
  while ((match = pattern.exec(String(text ?? "")))) {
    values.push(`${match[1]}원`);
  }
  return values;
}

function firstPriceString(text) {
  return priceStringsFromText(text)[0];
}

function currentPriceStringsFromLine(text) {
  if (/(?:배송비|적립|캐시|쿠폰|혜택|포인트)/i.test(String(text ?? ""))) return [];
  const prices = priceStringsFromText(text);
  if (prices.length === 0) return [];
  if (/(?:당|100ml|10ml|100g|1개|개당|g당|kg당|ml당)/i.test(String(text ?? ""))) {
    return prices.slice(0, 1);
  }
  return prices;
}

function ocrLineGeometry(line) {
  const box = Array.isArray(line?.bounding_box) ? line.bounding_box : [];
  if (box.length !== 4 || box.some((value) => !Number.isFinite(value))) return undefined;
  const [x, y, width, height] = box;
  const top = 1 - y - height;
  return {
    left: x,
    top,
    width,
    height,
    centerX: x + width / 2,
    centerY: top + height / 2,
  };
}

function coupangGridCellForLine(line) {
  const geometry = line.geometry;
  if (!geometry) return undefined;
  if (geometry.top < 0.12 || geometry.left >= 0.84) return undefined;
  const col = Math.max(0, Math.min(4, Math.round((geometry.centerX - 0.11) / 0.202)));
  const row = Math.max(0, Math.floor((geometry.top - 0.12) / 0.31));
  return { row, col, key: `${row}:${col}`, rowTop: 0.12 + row * 0.31 };
}

function titleCandidateLinesFromCardLines(lines, { rowTop } = {}) {
  const firstPriceIndex = lines.findIndex((line) => priceStringsFromText(line.text).length > 0);
  return lines
    .filter((line, index) => firstPriceIndex < 0 || index < firstPriceIndex)
    .filter((line) => !priceStringsFromText(line.text).length)
    .filter((line) => (Number.isFinite(rowTop) ? line.geometry.top >= rowTop + 0.095 : true))
    .map((line) => line.text)
    .filter((line) => !/^(?:광고|쿠팡추천|로켓배송|무료배송|무료반품|판매자로켓|내일|도착|오늘출발|와우할인|쿠폰|할인|별점|리뷰|\d+%?)$/i.test(line))
    .filter((line) => !/(?:최대\s*[0-9,]+원\s*적립|도착\s*예정|오늘출발|새벽\s*도착|무료배송|무료반품)/i.test(line))
    .slice(0, 8);
}

function buildProductCardCandidate({ cardLines, terms, normalizedTerms, targetWindow, cardKey, row, col, rowTop, titleLinesOverride }) {
  const titleLines = titleLinesOverride ?? titleCandidateLinesFromCardLines(cardLines, { rowTop });
  const titleNormalized = normalizeProductText(titleLines.join(" "));
  if (!normalizedTerms.every((term) => titleNormalized.includes(term))) return undefined;
  const priceCandidates = [];
  const likelyCurrentPriceCandidates = [];
  const discountedPriceCandidates = [];
  const currentPriceRecords = [];
  for (const line of cardLines) {
    const prices = priceStringsFromText(line.text);
    if (prices.length === 0) continue;
    for (const price of prices) {
      if (!priceCandidates.includes(price)) priceCandidates.push(price);
    }
    if (/%/.test(line.text)) {
      for (const price of currentPriceStringsFromLine(line.text)) {
        if (!discountedPriceCandidates.includes(price)) discountedPriceCandidates.push(price);
      }
    }
    for (const price of currentPriceStringsFromLine(line.text)) {
      if (!likelyCurrentPriceCandidates.includes(price)) likelyCurrentPriceCandidates.push(price);
      currentPriceRecords.push({ price, top: line.geometry.top, discounted: /%/.test(line.text) });
    }
  }
  if (priceCandidates.length === 0) return undefined;
  const verticalCurrentPriceCandidates =
    discountedPriceCandidates.length > 0
      ? discountedPriceCandidates
      : currentPriceRecords
          .sort((left, right) => right.top - left.top)
          .map((record) => record.price);
  const titleAnchor =
    cardLines.find((line) => normalizedTerms.some((term) => line.normalized.includes(term)) && line.geometry.top >= rowTop + 0.095) ??
    cardLines.find((line) => normalizedTerms.some((term) => line.normalized.includes(term))) ??
    cardLines[0];
  const bounds = targetWindow?.bounds ?? {};
  const clickPoint =
    Number.isFinite(Number(bounds.x)) &&
    Number.isFinite(Number(bounds.y)) &&
    Number.isFinite(Number(bounds.width)) &&
    Number.isFinite(Number(bounds.height)) &&
    titleAnchor
      ? {
          x: Math.round(Number(bounds.x) + titleAnchor.geometry.centerX * Number(bounds.width)),
          y: Math.round(Number(bounds.y) + titleAnchor.geometry.centerY * Number(bounds.height)),
        }
      : undefined;
  return {
    detection_mode: "grid_card_cluster",
    card_key: cardKey,
    row,
    col,
    matched_terms: terms,
    title_candidates: [...new Set(titleLines)],
    price_candidates: priceCandidates.slice(0, 8),
    current_price_candidates: [...new Set([...verticalCurrentPriceCandidates, ...likelyCurrentPriceCandidates])].slice(0, 4),
    lines: cardLines.map((line) => line.text).slice(0, 18),
    click_point: clickPoint,
  };
}

function gridProductCardCandidatesFromOcr(lines, terms, normalizedTerms, { targetWindow } = {}) {
  const groups = new Map();
  for (const line of lines) {
    const cell = coupangGridCellForLine(line);
    if (!cell) continue;
    const existing = groups.get(cell.key) ?? { ...cell, lines: [] };
    existing.lines.push(line);
    groups.set(cell.key, existing);
  }
  const cards = [];
  for (const group of [...groups.values()].sort((left, right) => left.row - right.row || left.col - right.col)) {
    const cardLines = group.lines.sort(
      (left, right) => left.geometry.top - right.geometry.top || left.geometry.left - right.geometry.left,
    );
    const candidate = buildProductCardCandidate({
      cardLines,
      terms,
      normalizedTerms,
      targetWindow,
      cardKey: group.key,
      row: group.row,
      col: group.col,
      rowTop: group.rowTop,
    });
    if (candidate) cards.push(candidate);
  }
  return cards;
}

function badgeOrNonProductLine(text) {
  return (
    /^(?:광고|쿠팡추천|로켓배송|무료배송|무료반품|판매자로켓|내일|도착|오늘출발|와우할인|쿠폰|할인|별점|리뷰|\d+%?)$/i.test(text) ||
    /(?:최대\s*[0-9,]+원\s*적립|도착\s*예정|오늘출발|새벽\s*도착|무료배송|무료반품|배송비)/i.test(text)
  );
}

function priceAnchoredProductCardCandidatesFromOcr(lines, terms, normalizedTerms, { targetWindow } = {}) {
  const candidateByKey = new Map();
  const priceLines = lines.filter(
    (line) =>
      line.geometry.left < 0.84 &&
      line.geometry.top >= 0.18 &&
      priceStringsFromText(line.text).length > 0 &&
      !/(?:적립|배송비|캐시|포인트)/i.test(line.text),
  );
  for (const priceLine of priceLines) {
    const cardLines = lines.filter((line) => {
      if (line.geometry.left >= 0.84) return false;
      if (line.geometry.top < 0.18) return false;
      const dx = Math.abs(line.geometry.centerX - priceLine.geometry.centerX);
      const dy = line.geometry.top - priceLine.geometry.top;
      return dx <= 0.105 && dy >= -0.135 && dy <= 0.09;
    });
    const titleLines = cardLines
      .filter((line) => !priceStringsFromText(line.text).length)
      .filter((line) => {
        const dy = line.geometry.top - priceLine.geometry.top;
        return dy >= -0.125 && dy <= 0.035;
      })
      .sort((left, right) => {
        const leftAllTerms = normalizedTerms.every((term) => left.normalized.includes(term)) ? 0 : 1;
        const rightAllTerms = normalizedTerms.every((term) => right.normalized.includes(term)) ? 0 : 1;
        return leftAllTerms - rightAllTerms || left.geometry.top - right.geometry.top || left.geometry.left - right.geometry.left;
      })
      .map((line) => line.text)
      .filter((line) => !badgeOrNonProductLine(line))
      .slice(0, 8);
    const titleNormalized = normalizeProductText(titleLines.join(" "));
    if (!normalizedTerms.every((term) => titleNormalized.includes(term))) continue;
    const row = Math.round(priceLine.geometry.top * 100);
    const col = Math.round(priceLine.geometry.centerX * 20);
    const candidate = buildProductCardCandidate({
      cardLines,
      terms,
      normalizedTerms,
      targetWindow,
      cardKey: `price:${row}:${col}`,
      row,
      col,
      rowTop: Math.max(0.0, priceLine.geometry.top - 0.14),
      titleLinesOverride: titleLines,
    });
    if (!candidate) continue;
    candidate.detection_mode = "price_anchor_card_cluster";
    candidate.title_candidates = [...new Set(titleLines)];
    candidate.sort_row = Math.round(priceLine.geometry.top * 3);
    candidate.sort_x = priceLine.geometry.centerX;
    const key = `${titleNormalized}:${candidate.sort_row}:${Math.round(priceLine.geometry.centerX * 10)}`;
    const existing = candidateByKey.get(key);
    if (!existing) {
      candidateByKey.set(key, candidate);
      continue;
    }
    existing.price_candidates = [...new Set([...existing.price_candidates, ...candidate.price_candidates])].slice(0, 8);
    existing.current_price_candidates = [...new Set([...existing.current_price_candidates, ...candidate.current_price_candidates])].slice(0, 4);
    existing.lines = [...new Set([...existing.lines, ...candidate.lines])].slice(0, 18);
  }
  return [...candidateByKey.values()].sort((left, right) => {
    return (left.sort_row ?? 0) - (right.sort_row ?? 0) || (left.sort_x ?? 0) - (right.sort_x ?? 0);
  });
}

function anchorProductCardCandidatesFromOcr(lines, terms, normalizedTerms, { targetWindow } = {}) {
  const cards = [];
  const seen = new Set();
  for (const anchor of lines) {
    if (!normalizedTerms.some((term) => anchor.normalized.includes(term))) continue;
    const sameColumn = lines.filter((line) => {
      const dx = Math.abs(line.geometry.centerX - anchor.geometry.centerX);
      const dy = line.geometry.top - anchor.geometry.top;
      return dx <= 0.13 && dy >= -0.04 && dy <= 0.14;
    });
    const combinedNormalized = normalizeProductText(sameColumn.map((line) => line.text).join(" "));
    if (!normalizedTerms.every((term) => combinedNormalized.includes(term))) continue;
    const key = sameColumn.map((line) => line.index).join(",");
    if (seen.has(key)) continue;
    seen.add(key);
    const rowTop = Math.max(0.12, Math.min(...sameColumn.map((line) => line.geometry.top)));
    const candidate = buildProductCardCandidate({
      cardLines: sameColumn,
      terms,
      normalizedTerms,
      targetWindow,
      cardKey: `anchor:${key}`,
      row: undefined,
      col: undefined,
      rowTop,
    });
    if (candidate) {
      candidate.detection_mode = "anchor_neighborhood_fallback";
      cards.push(candidate);
    }
  }
  return cards;
}

function productCardCandidatesFromOcr(ocr, question, { targetWindow } = {}) {
  const terms = productSearchTermsFromQuestion(question);
  if (terms.length === 0 || !Array.isArray(ocr?.lines)) return [];
  const normalizedTerms = terms.map(normalizeProductText).filter(Boolean);
  if (normalizedTerms.length === 0) return [];
  const lines = ocr.lines
    .map((line, index) => ({
      index,
      text: sanitizeCollectedText(line?.text),
      normalized: normalizeProductText(line?.text),
      geometry: ocrLineGeometry(line),
    }))
    .filter((line) => line.text && line.geometry && line.geometry.top >= 0.14)
    .sort((left, right) => left.geometry.top - right.geometry.top || left.geometry.left - right.geometry.left);
  const priceAnchoredCards = priceAnchoredProductCardCandidatesFromOcr(lines, terms, normalizedTerms, { targetWindow });
  if (priceAnchoredCards.length > 0) return priceAnchoredCards.slice(0, 10);
  const gridCards = gridProductCardCandidatesFromOcr(lines, terms, normalizedTerms, { targetWindow });
  if (gridCards.length > 0) return gridCards.slice(0, 10);
  return anchorProductCardCandidatesFromOcr(lines, terms, normalizedTerms, { targetWindow }).slice(0, 10);
}

function selectProductMatchForDetail(matches = [], { price, terms = [] } = {}) {
  const normalizedTerms = terms.map(normalizeProductText).filter(Boolean);
  const normalizedPrice = normalizeProductText(price);
  const candidates = matches.filter((match) => {
    const text = normalizeProductText(
      [
        ...(match.title_candidates ?? []),
        ...(match.lines ?? []),
        ...(match.price_candidates ?? []),
        ...(match.current_price_candidates ?? []),
      ].join(" "),
    );
    const termOk = normalizedTerms.length === 0 || normalizedTerms.every((term) => text.includes(term));
    const priceOk = !normalizedPrice || text.includes(normalizedPrice);
    return termOk && priceOk && match.click_point;
  });
  return candidates[0];
}

function compactOcrForOutput(ocr, maxChars = 2500) {
  if (!ocr) return undefined;
  return {
    ok: ocr.ok === true,
    line_count: Number(ocr.line_count ?? 0),
    text: sanitizeCollectedText(ocr.text).slice(0, maxChars),
    error: ocr.error,
  };
}

function buildScreenInformationSummary({ compactResult, ocr, targetWindow, question = "" }) {
  const ocrLines = Array.isArray(ocr?.lines)
    ? ocr.lines.map((line) => sanitizeCollectedText(line?.text)).filter(Boolean)
    : [];
  const browserUiNoise =
    /^(?:Harness OS|Harness|Gemini에게|모든 북마크|즐겨찾기|카테고리|전체|찾고 싶은 상품|쿠팡플레이|로켓배송|로켓프레시|다시 구매|쿠팡비즈|로켓직구|입점신청|고객센터|판매자 가입|장바구니|마이쿠팡|닫기|새 탭|Chrome|뒤로|앞으로|새로고침|주소창|탭 검색|로그아웃)$/i;
  const productOrOfferLines = [];
  const priceLines = [];
  const loginClues = [];
  for (const line of ocrLines) {
    if (/(?:로그아웃|마이쿠팡|님\b|고객센터|사용자|프로필)/.test(line)) {
      loginClues.push(line);
    }
    if (/(?:₩|원\b|[0-9]{1,3}(?:,[0-9]{3})+|%|할인|특가)/.test(line)) {
      priceLines.push(line);
    }
    if (
      line.length >= 2 &&
      !browserUiNoise.test(line) &&
      !/^[+•°=<>♡☆\s0-9.,:-]+$/.test(line) &&
      !/^(?:광고|더 알아보기|판매자|혜택|쿠팡|coupang)$/i.test(line)
    ) {
      productOrOfferLines.push(line);
    }
  }
  return {
    page: {
      application_name: compactResult?.application_name,
      window_title: compactResult?.window_title ?? targetWindow?.window_title,
      target_window_title: targetWindow?.window_title,
    },
    counts: {
      ax_elements: compactResult?.element_count,
      ocr_lines: ocrLines.length,
      product_or_offer_candidates: productOrOfferLines.length,
      price_candidates: priceLines.length,
      login_clues: loginClues.length,
    },
    product_or_offer_candidates: productOrOfferLines.slice(0, 60),
    price_candidates: priceLines.slice(0, 30),
    strict_product_matches: productCardCandidatesFromOcr(ocr, question, { targetWindow }),
    login_clues: [...new Set(loginClues)].slice(0, 20),
  };
}

function shouldCollectScrolledScreenInfo(question) {
  return /(?:쿠팡|coupang|상품|제품|product|item|정보\s*수집|수집기|스크롤|scroll|보이는\s*내용)/i.test(
    String(question ?? ""),
  );
}

function mergeScreenInformation(pages = []) {
  const merged = {
    pages: [],
    product_or_offer_candidates: [],
    price_candidates: [],
    strict_product_matches: [],
    login_clues: [],
  };
  const pushUnique = (target, values) => {
    const seen = new Set(target);
    for (const value of values ?? []) {
      const text = sanitizeCollectedText(value);
      if (!text || seen.has(text)) continue;
      seen.add(text);
      target.push(text);
    }
  };
  for (const page of pages) {
    const info = page?.screen_information;
    if (!info) continue;
    merged.pages.push({
      page_index: page.page_index,
      screenshot_raw: page.screenshot_raw,
      scroll: page.scroll,
      counts: info.counts,
    });
    pushUnique(merged.product_or_offer_candidates, info.product_or_offer_candidates);
    pushUnique(merged.price_candidates, info.price_candidates);
    for (const match of info.strict_product_matches ?? []) {
      const key = normalizeProductText(
        [
          ...(match.title_candidates ?? []),
          ...(match.current_price_candidates ?? []),
          ...(match.price_candidates ?? []),
        ].join(" "),
      );
      if (!key) continue;
      const exists = merged.strict_product_matches.some(
        (candidate) =>
          normalizeProductText(
            [
              ...(candidate.title_candidates ?? []),
              ...(candidate.current_price_candidates ?? []),
              ...(candidate.price_candidates ?? []),
            ].join(" "),
          ) === key,
      );
      if (!exists) {
        merged.strict_product_matches.push({
          page_index: page.page_index,
          ...match,
        });
      }
    }
    pushUnique(merged.login_clues, info.login_clues);
  }
  return {
    collected_page_count: merged.pages.length,
    pages: merged.pages,
    product_or_offer_candidates: merged.product_or_offer_candidates.slice(0, 60),
    price_candidates: merged.price_candidates.slice(0, 30),
    strict_product_matches: merged.strict_product_matches.slice(0, 10),
    login_clues: merged.login_clues.slice(0, 20),
  };
}

async function collectScrolledWindowInformation({ peekaboo, env, windowId, question, targetWindow, firstPage }) {
  const pages = [firstPage].filter(Boolean);
  if (!shouldCollectScrolledScreenInfo(question)) {
    return pages;
  }
  const scrollAmount = 8;
  let completedScrolls = 0;
  for (let index = 1; index <= 2; index += 1) {
    let scrollResult;
    try {
      scrollResult = await runProcess(
        peekaboo,
        [
          "scroll",
          "--no-remote",
          "--window-id",
          String(windowId),
          "--direction",
          "down",
          "--amount",
          String(scrollAmount),
          "--json",
        ],
        { timeoutMs: 8_000, env },
      );
    } catch (error) {
      pages.push({
        page_index: index,
        scroll: { ok: false, error: error.message },
      });
      break;
    }
    if (scrollResult.code !== 0) {
      pages.push({
        page_index: index,
        scroll: { ok: false, error: summarizePeekabooFailure(scrollResult) },
      });
      break;
    }
    completedScrolls += 1;
    let see;
    try {
      see = await runProcess(
        peekaboo,
        [
          "see",
          "--no-remote",
          "--window-id",
          String(windowId),
          "--capture-engine",
          "cg",
          "--json",
        ],
        { timeoutMs: 20_000, env },
      );
    } catch (error) {
      pages.push({
        page_index: index,
        scroll: { ok: true, direction: "down", amount: scrollAmount },
        capture: { ok: false, error: error.message },
      });
      break;
    }
    if (see.code !== 0) {
      pages.push({
        page_index: index,
        scroll: { ok: true, direction: "down", amount: scrollAmount },
        capture: { ok: false, error: summarizePeekabooFailure(see) },
      });
      break;
    }
    let parsed;
    try {
      parsed = JSON.parse(see.stdout);
    } catch {
      parsed = { text: see.stdout.trim() };
    }
    const compactResult = compactPeekabooSeeResult(parsed);
    const ocr = compactResult.screenshot_raw
      ? await runMacVisionOcr(compactResult.screenshot_raw)
      : undefined;
    const screenInformation = ocr
      ? buildScreenInformationSummary({
          compactResult,
          ocr,
          targetWindow,
          question,
        })
      : undefined;
    pages.push({
      page_index: index,
      screenshot_raw: compactResult.screenshot_raw,
      scroll: { ok: true, direction: "down", amount: scrollAmount },
      result: compactResult,
      ...(ocr ? { ocr: compactOcrForOutput(ocr, 1200) } : {}),
      ...(screenInformation ? { screen_information: screenInformation } : {}),
    });
  }
  if (completedScrolls > 0) {
    try {
      await runProcess(
        peekaboo,
        [
          "scroll",
          "--no-remote",
          "--window-id",
          String(windowId),
          "--direction",
          "up",
          "--amount",
          String(scrollAmount * completedScrolls),
          "--json",
        ],
        { timeoutMs: 8_000, env },
      );
    } catch {}
  }
  return pages;
}

function browserOpenTargetFromPrompt(prompt) {
  const text = currentUserInstruction(prompt);
  const coupangQuery = coupangSearchQueryFromPrompt(text);
  if (coupangQuery) {
    const url = new URL("https://www.coupang.com/np/search");
    url.searchParams.set("q", coupangQuery);
    return url.toString();
  }
  if (/(?:쿠팡|coupang)/i.test(text)) return "https://www.coupang.com/";
  const explicitUrl = text.match(/\bhttps?:\/\/[^\s<>"')]+/i)?.[0];
  if (explicitUrl) return normalizeBrowserUrl(explicitUrl);
  return undefined;
}

function coupangSearchQueryFromPrompt(text) {
  const raw = String(text ?? "").replace(/\s+/g, " ").trim();
  if (
    !/(?:쿠팡|coupang)/i.test(raw) ||
    !/(?:검색|찾아|찾기|search|가격|최저가|판매가|얼마|알아봐)/i.test(raw)
  ) {
    return undefined;
  }
  const patterns = [
    /(?:쿠팡|coupang)(?:에서|에)?\s+(.{1,80}?)(?:을|를)?\s*(?:검색|찾아|찾기|search)/i,
    /(?:검색|찾아|찾기|search)(?:어|어로|할|해|해서|하고)?\s+(.{1,80}?)(?:\s*(?:상품|제품|결과|보여|알려|수집|collect|product|item)|[.!?。]|$)/i,
    /(?:쿠팡|coupang)(?:을|를)?\s*(?:띄워서|열어서|접속해서|에서|에)?\s+(.{1,80}?)(?:의|을|를)?\s*(?:가격|최저가|판매가|얼마)(?:\s*(?:알아봐|알려줘|확인해|찾아줘|봐줘))?/i,
  ];
  for (const pattern of patterns) {
    const match = raw.match(pattern);
    const query = match?.[1]
      ?.replace(/(?:상품|제품|결과|목록|보여줘|알려줘|수집해|검색해|찾아줘|검색|찾아|찾기|가격|최저가|판매가|얼마|알아봐|search)$/i, "")
      .trim();
    if (query && !/(?:쿠팡|coupang)$/i.test(query)) return query.slice(0, 80);
  }
  return undefined;
}

function normalizeBrowserUrl(value) {
  const raw = String(value ?? "").trim();
  const target = raw || "https://www.coupang.com/";
  const urlText = /^(?:https?:)?\/\//i.test(target)
    ? target
    : /^(?:쿠팡|coupang)$/i.test(target)
      ? "https://www.coupang.com/"
      : `https://${target}`;
  const parsed = new URL(urlText);
  if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("unsupported_url_protocol");
  parsed.username = "";
  parsed.password = "";
  return parsed.toString();
}

function isCopilotUsageTool(toolName) {
  return String(toolName ?? "").toLowerCase().endsWith("harness_copilot_usage");
}

function isBrowserOpenTool(toolName) {
  return String(toolName ?? "").toLowerCase().endsWith("harness_browser_open");
}

function isScreenInspectTool(toolName) {
  return String(toolName ?? "").toLowerCase().endsWith("harness_screen_inspect");
}

function isCoupangDetailOpenTool(toolName) {
  return String(toolName ?? "").toLowerCase().endsWith("harness_coupang_product_detail_open");
}

function verificationEvidenceToolRelevant(question, toolName) {
  const text = String(question ?? "");
  const tool = String(toolName ?? "").toLowerCase();
  const routes = [
    [/(?:화면|브라우저|chrome|크롬|쿠팡|coupang)/i, /harness_screen_inspect$/],
    [/(?:gmail|메일|이메일)/i, /harness_gmail_(?:search|get)$/],
    [/(?:calendar|캘린더|일정)/i, /harness_calendar_(?:list|create)$/],
    [/(?:notion|노션)/i, /harness_notion_archive_create$/],
    [/(?:cron|크론|예약|스케줄)/i, /harness_cron_(?:list|create|remove)$/],
    [/(?:copilot|코파일럿|premium request)/i, /harness_copilot_usage$/],
    [/(?:alpaca|ibkr|트레이딩|포지션|주문|계좌)/i, /harness_alpaca_status$/],
    [/(?:사주|명리|운세|일진)/i, /harness_saju_(?:query|notebook_status)$/],
    [
      /(?:harness|하네스|저장소|repository|코드|파일|경로|라인|해시|구현|변경사항)/i,
      /harness_(?:knowledge_query|workspace_(?:read|search|stats|exec))$/,
    ],
  ];
  const matchedRoutes = routes.filter(([pattern]) => pattern.test(text));
  if (matchedRoutes.length > 0) {
    return matchedRoutes.some(([, toolPattern]) => toolPattern.test(tool));
  }
  return /^(?:web_search|web_fetch)$/.test(tool);
}

function browserOpenExecutionKeys(event = {}, context = {}) {
  return [
    event.runId,
    context.runId,
    event.toolCallId,
    context.toolCallId,
    event.toolUseId,
    context.toolUseId,
    event.itemId,
    context.itemId,
    event.id,
    context.id,
  ]
    .filter(Boolean)
    .map(String);
}

function screenInspectExecutionKeys(event = {}, context = {}) {
  return [
    event.runId,
    context.runId,
    event.sessionKey,
    context.sessionKey,
    event.sessionId,
    context.sessionId,
    event.toolCallId,
    context.toolCallId,
    event.toolUseId,
    context.toolUseId,
    event.itemId,
    context.itemId,
    event.id,
    context.id,
  ]
    .filter(Boolean)
    .map(String);
}

function coupangDetailOpenExecutionKeys(event = {}, context = {}) {
  return screenInspectExecutionKeys(event, context);
}

function currentSenderId(prompt) {
  const raw = String(prompt ?? "");
  const marker = "Current user request:";
  const markerIndex = raw.indexOf(marker);
  const beforeCurrentRequest = markerIndex >= 0 ? raw.slice(0, markerIndex) : raw;
  const metadata = beforeCurrentRequest.split(/\n\n/, 1)[0];
  const contextMatch = metadata.match(/^<conversation_context>\s*(\{[\s\S]*?\})\s*<\/conversation_context>/i);
  if (contextMatch) {
    try {
      const context = JSON.parse(contextMatch[1]);
      return context?.sender?.id ? String(context.sender.id) : undefined;
    } catch {
      return undefined;
    }
  }
  if (!/^Conversation info\b/i.test(metadata)) return undefined;
  return metadata.match(
    /"sender"\s*:\s*\{[\s\S]{0,300}?"id"\s*:\s*"([^"]+)"/,
  )?.[1];
}

function configuredOwnerSenderIds() {
  return new Set([
    ...pluginOwnerSenderIds,
    ...String(process.env.OPENCLAW_OWNER_SENDER_IDS ?? "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  ]);
}

function isOwnerOnlyDiscordSession(sessionKey, config, ownerIds) {
  const channelId = String(sessionKey ?? "").match(/^agent:[^:]+:discord:channel:(\d+)$/)?.[1];
  if (!channelId || ownerIds.size === 0) return false;
  for (const guild of Object.values(config?.channels?.discord?.guilds ?? {})) {
    const channel = guild?.channels?.[channelId];
    if (!channel) continue;
    const allowed = Array.isArray(channel.users)
      ? channel.users.map(String)
      : Array.isArray(guild?.users)
        ? guild.users.map(String)
        : [];
    return allowed.length > 0 && allowed.every((senderId) => ownerIds.has(senderId));
  }
  return false;
}

function discordSessionChannelKnown(sessionKey, config) {
  const channelId = String(sessionKey ?? "").match(/^agent:[^:]+:discord:channel:(\d+)$/)?.[1];
  if (!channelId) return false;
  for (const guild of Object.values(config?.channels?.discord?.guilds ?? {})) {
    if (guild?.channels?.[channelId]) return true;
  }
  return false;
}

function contextSenderIds(context = {}) {
  return [
    context.requesterSenderId,
    context.senderId,
    context.sourceSenderId,
    context.sender?.id,
    context.source?.senderId,
    context.source?.sender?.id,
    context.message?.senderId,
    context.message?.sender?.id,
  ]
    .filter(Boolean)
    .map(String);
}

function currentSenderIsOwner(prompt, context = {}, event = {}) {
  const senderId = currentSenderId(prompt);
  const sessionKeys = [
    context.sessionKey,
    context.sessionId,
    context.session?.key,
    event.sessionKey,
    event.sessionId,
    event.session?.key,
  ]
    .filter(Boolean)
    .map(String);
  const ownerIds = configuredOwnerSenderIds();
  const explicitSenderIds = [senderId, ...contextSenderIds(context)].filter(Boolean);
  if (explicitSenderIds.length > 0 && explicitSenderIds.some((id) => !ownerIds.has(id))) {
    return false;
  }
  return (
    context.senderIsOwner === true ||
    (Boolean(senderId) && ownerIds.has(senderId)) ||
    contextSenderIds(context).some((id) => ownerIds.has(id)) ||
    sessionKeys.some((key) => pluginOwnerSessionKeys.has(key))
  );
}

function currentUserRequest(prompt) {
  const raw = String(prompt ?? "");
  const marker = "Current user request:";
  const index = raw.lastIndexOf(marker);
  return index >= 0
    ? raw.slice(index + marker.length)
    : raw.replace(/<conversation_context>[\s\S]*?<\/conversation_context>/gi, "");
}

function currentUserInstruction(prompt) {
  return currentUserRequest(prompt).split(/^---\s*$/m, 1)[0].trim();
}

export function isRawPumpShellCall(toolName, params = {}) {
  if (!isShellTool(toolName)) return false;
  let serialized;
  try {
    serialized = JSON.stringify(params);
  } catch {
    return true;
  }
  return (
    /\/pump\/cmd|farm\/[^\s"'`]*pump|mosquitto_(?:pub|sub)[\s\S]{0,200}(?:pump|relay|펌프|릴레이)/i.test(
      serialized,
    ) ||
    /(?:펌프|릴레이|\bpump\b|\brelay\b)[\s\S]{0,120}(?:\bon\b|\boff\b|\b켜|\b꺼|-m\b)/i.test(
      serialized,
    )
  );
}

export function isHighImpactBrowserShellCall(toolName, params = {}) {
  if (!isShellTool(toolName)) return false;
  try {
    const serialized = JSON.stringify(params);
    const compact = serialized.toLowerCase().replace(/[^a-z가-힣]/g, "");
    return (
      HIGH_IMPACT_BROWSER_BRIDGE_COMMAND.test(serialized) ||
      (/openclaw_codex_bridge\.py/i.test(serialized) &&
        /(?:browserfill|coupangsetup|coupangcart|coupangpayapprove|coupangpay|coupangcheckout)/i.test(
          compact,
        )) ||
      (/openclaw_codex_bridge\.py/i.test(serialized) &&
        /(?:browser|coupang|cou[\s\S]*pang|pang[\s\S]*cou)/i.test(compact) &&
        /(?:fill|setup|cart|pay|approve|checkout)/i.test(compact)) ||
      (/openclaw_codex_bridge\.py/i.test(serialized) &&
        /browser|coupang/i.test(serialized) &&
        /fill|setup|cart|pay|approve/i.test(serialized))
    );
  } catch {
    return true;
  }
}

export function isPeekabooShellCall(toolName, params = {}) {
  if (!isShellTool(toolName)) return false;
  try {
    const serialized = JSON.stringify(params);
    return /\bpeekaboo\b|PEEKABOO_BRIDGE_SOCKET|OpenClaw\/bridge\.sock/i.test(serialized);
  } catch {
    return true;
  }
}

function isKnowledgeBypassTool(toolName) {
  const name = String(toolName ?? "").toLowerCase();
  return (
    isShellTool(name) ||
    name === "memory_search" ||
    name === "memory_get" ||
    name === "harness_workspace_search" ||
    name === "harness_workspace_read"
  );
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
      env: { ...process.env, ...(options.env ?? {}) },
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

async function deliverOwnerScreenEvidence(sessionKey, result) {
  if (!process.env.OPENCLAW_GATEWAY_PORT) return { attempted: false };
  const channelMatch = String(sessionKey ?? "").match(/:discord:channel:(\d+)$/);
  if (!channelMatch) return { attempted: false };
  const mediaPaths = disposablePeekabooCapturePaths(result);
  if (mediaPaths.length === 0) return { attempted: false };
  const executable = "/opt/homebrew/bin/openclaw";
  if (!fs.existsSync(executable)) return { attempted: false };
  const text = deterministicCoupangEvidenceReply(result);
  const delivery = await runProcess(
    executable,
    [
      "message",
      "send",
      "--channel",
      "discord",
      "--target",
      `channel:${channelMatch[1]}`,
      "--message",
      composeEvidenceReplyText({
        baseText: text,
        pendingText: text,
        evidenceText: "증빙: 첨부한 실제 화면 캡처",
        verificationFailed: false,
      }),
      "--media",
      mediaPaths[0],
      "--json",
    ],
    { cwd: os.homedir(), timeoutMs: 30_000 },
  );
  if (delivery.code !== 0) {
    return { attempted: true, ok: false, error: "evidence_delivery_failed" };
  }
  let parsed;
  try {
    parsed = JSON.parse(delivery.stdout);
  } catch {
    return { attempted: true, ok: false, error: "evidence_delivery_invalid_response" };
  }
  if (
    parsed?.action !== "send" ||
    parsed?.channel !== "discord" ||
    parsed?.dryRun !== false ||
    parsed?.payload?.deliveryStatus !== "sent" ||
    !/^\d+$/.test(String(parsed?.messageId ?? "")) ||
    parsed?.payload?.result?.receipt?.primaryPlatformMessageId !== parsed.messageId ||
    !Array.isArray(parsed?.payload?.payloadOutcomes) ||
    parsed.payload.payloadOutcomes.length === 0 ||
    !parsed?.payload?.payloadOutcomes?.every((outcome) => outcome?.status === "sent")
  ) {
    return { attempted: true, ok: false, error: "evidence_delivery_not_confirmed" };
  }
  let trashed = 0;
  for (const imagePath of mediaPaths) {
    let identity;
    try {
      const stat = fs.statSync(imagePath);
      identity = { dev: stat.dev, ino: stat.ino };
    } catch {
      continue;
    }
    if (moveDisposableCaptureToTrash(imagePath, identity)) trashed += 1;
  }
  return {
    attempted: true,
    ok: true,
    attachmentCount: 1,
    trashedCaptureCount: trashed,
  };
}

function toolText(value, isError = false) {
  return {
    content: [{ type: "text", text: typeof value === "string" ? value : JSON.stringify(value) }],
    ...(isError ? { isError: true } : {}),
  };
}

function findPeekabooBinary() {
  const candidates = [
    process.env.PEEKABOO_BIN,
    "/opt/homebrew/bin/peekaboo",
    "/usr/local/bin/peekaboo",
    "/opt/homebrew/Cellar/peekaboo/3.2.0/bin/peekaboo",
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      if (fs.existsSync(candidate)) return candidate;
    } catch {
      // Try the next candidate.
    }
  }
  return undefined;
}

function peekabooBridgeSocketCandidates() {
  const home = process.env.HOME ?? "";
  return [
    process.env.PEEKABOO_BRIDGE_SOCKET,
    path.join(home, "Library", "Application Support", "OpenClaw", "bridge.sock"),
    path.join(home, "Library", "Application Support", "Peekaboo", "bridge.sock"),
  ]
    .filter(Boolean)
    .filter((value, index, values) => values.indexOf(value) === index);
}

function summarizePeekabooFailure(result) {
  const combined = `${result.stdout ?? ""}\n${result.stderr ?? ""}`.trim();
  return combined.slice(0, 600);
}

function bridgeSuccessPayload(statusJson) {
  const candidates = statusJson?.data?.candidates;
  if (!Array.isArray(candidates) || candidates.length !== 1) return undefined;
  const result = candidates[0]?.result;
  if (!result || typeof result !== "object" || result.failure) return undefined;
  const success = result.success?._0;
  if (!success || typeof success !== "object") return undefined;
  const hostKind = String(success.hostKind ?? "").toLowerCase();
  if (!["gui", "ondemand"].includes(hostKind)) return undefined;
  const supported = Array.isArray(success.supportedOperations)
    ? success.supportedOperations.map(String)
    : [];
  const captureTags = Array.isArray(success.permissionTags?.captureScreen)
    ? success.permissionTags.captureScreen.map(String)
    : [];
  if (!supported.includes("captureScreen") || !captureTags.includes("screenRecording")) {
    return undefined;
  }
  return success;
}

async function selectPeekabooBridge(peekaboo) {
  const candidates = peekabooBridgeSocketCandidates();
  const attempted = [];
  for (const socketPath of candidates) {
    if (!fs.existsSync(socketPath)) {
      attempted.push({ socketPath, exists: false });
      continue;
    }
    const env = { PEEKABOO_BRIDGE_SOCKET: socketPath };
    let status;
    try {
      status = await runProcess(peekaboo, ["bridge", "status", "--json"], {
        timeoutMs: 3_000,
        env,
      });
    } catch (error) {
      attempted.push({ socketPath, exists: true, error: error.message });
      continue;
    }
    if (status.code !== 0) {
      attempted.push({
        socketPath,
        exists: true,
        error: "peekaboo_bridge_status_failed",
        detail: summarizePeekabooFailure(status),
      });
      continue;
    }
    let statusJson;
    try {
      statusJson = JSON.parse(status.stdout);
    } catch {
      attempted.push({
        socketPath,
        exists: true,
        error: "peekaboo_bridge_status_invalid_json",
        detail: summarizePeekabooFailure(status),
      });
      continue;
    }
    const success = bridgeSuccessPayload(statusJson);
    if (success) {
      return { socketPath, env, status: statusJson, bridge: success };
    }
    attempted.push({
      socketPath,
      exists: true,
      error: "peekaboo_bridge_not_ready",
      status: statusJson.data ?? statusJson,
    });
  }
  return { attempted };
}

async function inspectPreferredChromeWindow({ peekaboo, env, socketPath, question, directFailure = "screen_mode_skipped" }) {
  let windowList;
  try {
    windowList = await runProcess(peekaboo, ["window", "list", "--no-remote", "--app", "Google Chrome", "--json"], {
      timeoutMs: 8_000,
      env,
    });
  } catch (error) {
    return {
      ok: false,
      error: "peekaboo_screen_inspect_failed",
      socketPath,
      detail: directFailure,
      fallback_error: error.message,
    };
  }
  if (windowList.code !== 0) {
    return {
      ok: false,
      error: "peekaboo_screen_inspect_failed",
      socketPath,
      detail: directFailure,
      fallback_error: summarizePeekabooFailure(windowList),
    };
  }
  let parsedWindowList;
  try {
    parsedWindowList = JSON.parse(windowList.stdout);
  } catch {
    parsedWindowList = undefined;
  }
  const preferredWindowPattern = /(?:쿠팡|coupang)/i.test(question)
    ? /(?:쿠팡|coupang)/i
    : undefined;
  const bestWindow = selectBestPeekabooWindow(
    parsedWindowList?.data?.windows ?? [],
    preferredWindowPattern,
  );
  if (!bestWindow?.window_id) {
    return {
      ok: false,
      error: "peekaboo_screen_inspect_failed",
      socketPath,
      detail: directFailure,
      fallback_error: "chrome_window_not_found",
    };
  }
  let fallbackSee;
  try {
    fallbackSee = await runProcess(
      peekaboo,
      [
        "see",
        "--no-remote",
        "--window-id",
        String(bestWindow.window_id),
        "--capture-engine",
        "cg",
        "--json",
      ],
      { timeoutMs: 20_000, env },
    );
  } catch (error) {
    fallbackSee = {
      code: 124,
      stdout: "",
      stderr: error.message,
      timedOut: true,
    };
  }
  if (fallbackSee.code !== 0) {
    return {
      ok: false,
      error: "peekaboo_screen_inspect_failed",
      socketPath,
      detail: directFailure,
      fallback_error: summarizePeekabooFailure(fallbackSee),
      targetWindow: {
        window_id: bestWindow.window_id,
        window_title: bestWindow.window_title,
        bounds: bestWindow.bounds,
      },
    };
  }
  let fallbackParsed;
  try {
    fallbackParsed = JSON.parse(fallbackSee.stdout);
  } catch {
    fallbackParsed = { text: fallbackSee.stdout.trim() };
  }
  const compactResult = compactPeekabooSeeResult(fallbackParsed);
  const ocr =
    compactResult.screenshot_raw && /(?:쿠팡|coupang|상품|제품|product|item)/i.test(question)
      ? await runMacVisionOcr(compactResult.screenshot_raw)
      : undefined;
  const screenInformation = ocr
    ? buildScreenInformationSummary({
        compactResult,
        ocr,
        targetWindow: bestWindow,
        question,
      })
    : undefined;
  const firstCollectedPage = {
    page_index: 0,
    screenshot_raw: compactResult.screenshot_raw,
    scroll: { ok: true, direction: "initial", amount: 0 },
    result: compactResult,
    ...(ocr ? { ocr: compactOcrForOutput(ocr, 1800) } : {}),
    ...(screenInformation ? { screen_information: screenInformation } : {}),
  };
  const collectedPages = await collectScrolledWindowInformation({
    peekaboo,
    env,
    windowId: bestWindow.window_id,
    question,
    targetWindow: bestWindow,
    firstPage: firstCollectedPage,
  });
  return {
    ok: true,
    socketPath,
    method: "window-id-cg-fallback",
    directFailure,
    targetWindow: {
      app: parsedWindowList?.data?.target_application_info?.app_name,
      bundle_id: parsedWindowList?.data?.target_application_info?.bundle_id,
      window_id: bestWindow.window_id,
      window_title: bestWindow.window_title,
      bounds: bestWindow.bounds,
    },
    result: {
      ...compactResult,
      ...(!shouldCollectScrolledScreenInfo(question) && ocr
        ? { ocr: compactOcrForOutput(ocr, 1600) }
        : {}),
      ...(!shouldCollectScrolledScreenInfo(question) && screenInformation
        ? { screen_information: screenInformation }
        : {}),
      smart_collection: {
        strategy: "window-id-cg-ocr-scroll",
        scroll_enabled: shouldCollectScrolledScreenInfo(question),
        pages: collectedPages.map((page) => ({
          page_index: page.page_index,
          screenshot_raw: page.screenshot_raw,
          scroll: page.scroll,
          counts: page.screen_information?.counts,
        })),
        merged: mergeScreenInformation(collectedPages),
      },
    },
  };
}

async function inspectMacScreen(params = {}) {
  const peekaboo = findPeekabooBinary();
  if (!peekaboo) {
    return {
      ok: false,
      error: "peekaboo_not_installed",
      action: "Install Peekaboo or set PEEKABOO_BIN to the CLI path.",
    };
  }
  const selectedBridge = await selectPeekabooBridge(peekaboo);
  if (!selectedBridge.socketPath) {
    return {
      ok: false,
      error: selectedBridge.attempted?.some((entry) => entry.exists)
        ? "peekaboo_bridge_not_ready"
        : "peekaboo_bridge_socket_missing",
      attempted: selectedBridge.attempted,
      action:
        "Start the OpenClaw or Peekaboo GUI bridge and confirm a bridge socket exists before asking for screen inspection.",
    };
  }
  const { socketPath, env } = selectedBridge;

  let permissions;
  try {
    permissions = await runProcess(peekaboo, ["permissions"], { timeoutMs: 3_000, env });
  } catch (error) {
    return {
      ok: false,
      error: "peekaboo_permissions_timeout_or_error",
      socketPath,
      detail: error.message,
    };
  }
  if (permissions.code !== 0 || /Not Granted/i.test(permissions.stdout)) {
    return {
      ok: false,
      error: "peekaboo_permissions_not_granted",
      socketPath,
      permissions: permissions.stdout.trim(),
      action:
        "Grant Screen Recording and Accessibility to OpenClaw/Peekaboo in macOS Privacy & Security.",
    };
  }

  const question = String(params.question ?? "").trim() || "Describe the currently visible screen briefly.";
  if (/(?:쿠팡|coupang)/i.test(question)) {
    const preferredChromeResult = await inspectPreferredChromeWindow({
      peekaboo,
      env,
      socketPath,
      question,
      directFailure: "screen_mode_skipped_for_coupang_window_preference",
    });
    if (preferredChromeResult.ok) return preferredChromeResult;
  }
  let see;
  try {
    see = await runProcess(
      peekaboo,
      [
        "see",
        "--mode",
        "screen",
        "--screen-index",
        "0",
        "--analyze",
        question.slice(0, 500),
        "--json",
      ],
      { timeoutMs: 15_000, env },
    );
  } catch (error) {
    see = {
      code: 124,
      stdout: "",
      stderr: error.message,
      timedOut: true,
    };
  }
  if (see.code !== 0) {
    const directFailure = summarizePeekabooFailure(see);
    let windowList;
    try {
      windowList = await runProcess(peekaboo, ["window", "list", "--no-remote", "--app", "Google Chrome", "--json"], {
        timeoutMs: 8_000,
        env,
      });
    } catch (error) {
      return {
        ok: false,
        error: "peekaboo_screen_inspect_failed",
        socketPath,
        detail: directFailure,
        fallback_error: error.message,
      };
    }
    if (windowList.code === 0) {
      let parsedWindowList;
      try {
        parsedWindowList = JSON.parse(windowList.stdout);
      } catch {
        parsedWindowList = undefined;
      }
      const preferredWindowPattern = /(?:쿠팡|coupang)/i.test(question)
        ? /(?:쿠팡|coupang)/i
        : undefined;
      const bestWindow = selectBestPeekabooWindow(
        parsedWindowList?.data?.windows ?? [],
        preferredWindowPattern,
      );
      if (bestWindow?.window_id) {
        let fallbackSee;
        try {
          fallbackSee = await runProcess(
            peekaboo,
            [
              "see",
              "--no-remote",
              "--window-id",
              String(bestWindow.window_id),
              "--capture-engine",
              "cg",
              "--json",
            ],
            { timeoutMs: 20_000, env },
          );
        } catch (error) {
          fallbackSee = {
            code: 124,
            stdout: "",
            stderr: error.message,
            timedOut: true,
          };
        }
        if (fallbackSee.code === 0) {
          let fallbackParsed;
          try {
            fallbackParsed = JSON.parse(fallbackSee.stdout);
          } catch {
            fallbackParsed = { text: fallbackSee.stdout.trim() };
          }
          const compactResult = compactPeekabooSeeResult(fallbackParsed);
          const ocr =
            compactResult.screenshot_raw && /(?:쿠팡|coupang|상품|제품|product|item)/i.test(question)
              ? await runMacVisionOcr(compactResult.screenshot_raw)
              : undefined;
          const screenInformation = ocr
            ? buildScreenInformationSummary({
                compactResult,
                ocr,
                targetWindow: bestWindow,
                question,
              })
            : undefined;
          const firstCollectedPage = {
            page_index: 0,
            screenshot_raw: compactResult.screenshot_raw,
            scroll: { ok: true, direction: "initial", amount: 0 },
            result: compactResult,
            ...(ocr ? { ocr: compactOcrForOutput(ocr, 1800) } : {}),
            ...(screenInformation ? { screen_information: screenInformation } : {}),
          };
          const collectedPages = await collectScrolledWindowInformation({
            peekaboo,
            env,
            windowId: bestWindow.window_id,
            question,
            targetWindow: bestWindow,
            firstPage: firstCollectedPage,
          });
          return {
            ok: true,
            socketPath,
            method: "window-id-cg-fallback",
            directFailure,
            targetWindow: {
              app: parsedWindowList?.data?.target_application_info?.app_name,
              bundle_id: parsedWindowList?.data?.target_application_info?.bundle_id,
              window_id: bestWindow.window_id,
              window_title: bestWindow.window_title,
              bounds: bestWindow.bounds,
            },
            result: {
              ...compactResult,
              ...(!shouldCollectScrolledScreenInfo(question) && ocr
                ? { ocr: compactOcrForOutput(ocr, 1600) }
                : {}),
              ...(!shouldCollectScrolledScreenInfo(question) && screenInformation
                ? { screen_information: screenInformation }
                : {}),
              smart_collection: {
                strategy: "window-id-cg-ocr-scroll",
                scroll_enabled: shouldCollectScrolledScreenInfo(question),
                pages: collectedPages.map((page) => ({
                  page_index: page.page_index,
                  screenshot_raw: page.screenshot_raw,
                  scroll: page.scroll,
                  counts: page.screen_information?.counts,
                })),
                merged: mergeScreenInformation(collectedPages),
              },
            },
          };
        }
        return {
          ok: false,
          error: "peekaboo_screen_inspect_failed",
          socketPath,
          detail: directFailure,
          fallback_error: summarizePeekabooFailure(fallbackSee),
          targetWindow: {
            window_id: bestWindow.window_id,
            window_title: bestWindow.window_title,
            bounds: bestWindow.bounds,
          },
        };
      }
    }
    return {
      ok: false,
      error: "peekaboo_screen_inspect_failed",
      socketPath,
      detail: directFailure,
      fallback_error:
        windowList.code === 0 ? "chrome_window_not_found" : summarizePeekabooFailure(windowList),
    };
  }
  let parsed;
  try {
    parsed = JSON.parse(see.stdout);
  } catch {
    parsed = { text: see.stdout.trim() };
  }
  return {
    ok: true,
    socketPath,
    result: parsed,
  };
}

async function openCoupangProductDetail(params = {}) {
  const productTermsText = Array.isArray(params.productNameTerms)
    ? params.productNameTerms.join(" ")
    : params.productNameTerms;
  const question = [
    "쿠팡 검색 결과에서 상품 상세 진입",
    productTermsText,
    params.price,
  ]
    .filter(Boolean)
    .join(" ");
  let inspected = await inspectMacScreen({ question });
  if (!inspected.ok) return inspected;
  let matches = inspected.result?.smart_collection?.merged?.strict_product_matches ?? [];
  let terms = Array.isArray(params.productNameTerms)
    ? params.productNameTerms
    : sanitizeCollectedText(params.productNameTerms)
        .split(/\s+/)
        .filter(Boolean);
  let match = selectProductMatchForDetail(matches, {
    price: params.price,
    terms,
  });
  if (!match && terms.length === 0) {
    const fallbackTerms = productSearchTermsFromCoupangWindowTitle(inspected.targetWindow?.window_title);
    if (fallbackTerms.length >= 2) {
      terms = fallbackTerms;
      inspected = await inspectMacScreen({
        question: `쿠팡에서 ${terms.join(" ")} 검색 결과 중 ${params.price ?? ""} 상품 상세 진입`,
      });
      if (!inspected.ok) return inspected;
      matches = inspected.result?.smart_collection?.merged?.strict_product_matches ?? [];
      match = selectProductMatchForDetail(matches, {
        price: params.price,
        terms,
      });
    }
  }
  if (!match && terms.length >= 2) {
    const searchUrl = new URL("https://www.coupang.com/np/search");
    searchUrl.searchParams.set("q", terms.join(" "));
    const openSearch = await runProcess("/usr/bin/open", ["-a", "Google Chrome", searchUrl.toString()], {
      timeoutMs: 10_000,
    });
    if (openSearch.code === 0) {
      await new Promise((resolve) => setTimeout(resolve, 2500));
      inspected = await inspectMacScreen({
        question: `쿠팡에서 ${terms.join(" ")} 검색 결과 중 ${params.price ?? ""} 상품 상세 진입`,
      });
      if (!inspected.ok) return inspected;
      matches = inspected.result?.smart_collection?.merged?.strict_product_matches ?? [];
      match = selectProductMatchForDetail(matches, {
        price: params.price,
        terms,
      });
    }
  }
  if (!match?.click_point) {
    return {
      ok: false,
      error: "coupang_product_detail_target_not_found",
      inspected,
      hint: "No exact product card with all requested terms and price was found on the current Coupang screen.",
    };
  }
  const peekaboo = findPeekabooBinary();
  if (!peekaboo) {
    return { ok: false, error: "peekaboo_not_installed" };
  }
  const selectedBridge = await selectPeekabooBridge(peekaboo);
  if (!selectedBridge.socketPath) {
    return { ok: false, error: "peekaboo_bridge_not_ready", attempted: selectedBridge.attempted };
  }
  const windowId = inspected.targetWindow?.window_id;
  const clickArgs = [
    "click",
    "--no-remote",
    "--coords",
    `${match.click_point.x},${match.click_point.y}`,
    "--json",
  ];
  if (windowId) clickArgs.splice(2, 0, "--window-id", String(windowId));
  const click = await runProcess(peekaboo, clickArgs, {
    timeoutMs: 10_000,
    env: selectedBridge.env,
  });
  if (click.code !== 0) {
    return {
      ok: false,
      error: "coupang_product_detail_click_failed",
      target: match,
      detail: summarizePeekabooFailure(click),
    };
  }
  await new Promise((resolve) => setTimeout(resolve, 1500));
  return {
    ok: true,
    action: "opened_coupang_product_detail_candidate",
    target: match,
    click: {
      point: match.click_point,
    },
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
  api.registerTool({
    name: "harness_smartfarm_pump_control",
    description:
      "Fail-closed smartfarm pump control. OFF is published with retries. ON returns a clear safety block until an independent hardware watchdog is live-verified.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: [],
      properties: {
        zone: {
          type: ["string", "integer"],
          description:
            "Canonical zone ID. Map semantic ordinals such as '두 번째 구역' to zone2; a bare positive integer is also accepted and canonicalized server-side.",
        },
        action: { type: "string", enum: ["on", "off"] },
        durationSeconds: { type: "integer", minimum: 1, maximum: 15, default: 5 },
        dryRun: { type: "boolean", default: false },
        confirmationBound: {
          type: "boolean",
          description: "Internal plugin-owned field. The model must omit it.",
        },
      },
    },
    async execute(_id, params) {
      try {
        if (!params.confirmationBound && !params.dryRun) {
          return toolText({ ok: false, error: "confirmation_not_bound_to_user_turn" }, true);
        }
        const missingFields = ["zone", "action"].filter((field) => !params[field]);
        if (missingFields.length) {
          return toolText({
            ok: false,
            pending: true,
            missingFields,
            message: `Ask only for: ${missingFields.join(", ")}`,
          });
        }
        const args = [
          path.join(harnessRepoRoot(), "scripts", "smartfarm_pump_control.py"),
          "--zone",
          String(params.zone),
          "--action",
          String(params.action),
          "--duration-seconds",
          String(params.durationSeconds ?? 5),
        ];
        if (params.confirmationBound || params.dryRun) args.push("--confirmed");
        if (params.dryRun) args.push("--dry-run");
        const result = await runProcess(python(), args, { timeoutMs: 10_000 });
        return toolText(result.stdout || result.stderr, result.code !== 0);
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  });
  api.registerTool({
    name: "harness_knowledge_query",
    description:
      "Incrementally index the live Harness worktree and return compact, ranked, line-numbered evidence for any Harness domain or project-status question. Use before broad repository searches.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: ["question"],
      properties: {
        question: { type: "string", minLength: 1, maxLength: 4000 },
        maxFiles: { type: "integer", minimum: 1, maximum: 30, default: 12 },
        maxExcerpts: { type: "integer", minimum: 1, maximum: 20, default: 8 },
        forceRefresh: { type: "boolean", default: false },
        reuseOnly: {
          type: "boolean",
          default: false,
          description: "Internal per-turn duplicate-call suppression flag.",
        },
      },
    },
    async execute(_id, params) {
      try {
        if (params.reuseOnly) {
          return toolText({
            ok: true,
            reused: true,
            instruction:
              "Reuse the first harness_knowledge_query result from this turn; do not search again.",
          });
        }
        const args = [
          path.join(harnessRepoRoot(), "scripts", "harness_knowledge_index.py"),
          "--repo",
          harnessRepoRoot(),
          "--question",
          params.question,
          "--max-files",
          String(params.maxFiles ?? 12),
          "--max-excerpts",
          String(params.maxExcerpts ?? 8),
        ];
        if (params.forceRefresh) args.push("--force-refresh");
        const result = await runProcess(python(), args, { timeoutMs: 120_000 });
        return toolText(result.stdout || result.stderr, result.code !== 0);
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  });
  bridgeTool(
    "harness_alpaca_status",
    "Fetch live Alpaca paper-trading account, positions, orders, signals, and KPI state read-only. Use after repository knowledge retrieval for current Turtle status.",
    () => ["alpaca-status", "--format", "json"],
    { type: "object", additionalProperties: false, properties: {} },
  );
  bridgeTool(
    "harness_copilot_usage",
    "Read the sanitized laptop Copilot CLI usage snapshot. Use for Copilot billing, model, session, or usage-cause questions before giving estimates.",
    (p) => ["copilot-usage", "--max-age-seconds", String(p.maxAgeSeconds ?? 900)],
    {
      type: "object", additionalProperties: false,
      properties: { maxAgeSeconds: { type: "integer", minimum: 60, maximum: 3600, default: 900 } },
    },
  );
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
    "harness_gmail_oauth_mobile_start",
    "Create a five-minute, one-use Google approval link for the CEO's Tailnet-connected mobile. Use only after Gmail or Calendar returns invalid_grant; send the returned auth_url to the requesting Discord conversation without altering it.",
    () => ["gmail-oauth-mobile-start"],
    { type: "object", additionalProperties: false, properties: {} },
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
  api.registerTool((toolContext = {}) => ({
    name: "harness_browser_open",
    description:
      "Open a URL in the Mac GUI browser only. Use for owner requests like 'browser 띄워서 쿠팡 접속해'. It does not log in, add to cart, buy, pay, submit forms, or scrape private data.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: ["url"],
      properties: {
        url: {
          type: "string",
          minLength: 1,
          maxLength: 2000,
          description: "HTTP/HTTPS URL to open. Use https://www.coupang.com/ for Coupang homepage.",
        },
      },
    },
    async execute(toolCallId, params) {
      try {
        const executionKeys = browserOpenExecutionKeys({ toolCallId, id: toolCallId }, toolContext);
        const tokenState = executionKeys
          .map((key) => browserOpenExecutionTokens.get(key))
          .find((state) => state && state.expiresAt > Date.now());
        if (!tokenState || tokenState.expiresAt <= Date.now()) {
          for (const key of executionKeys) browserOpenExecutionTokens.delete(key);
          return toolText({ ok: false, error: "browser_open_not_bound_to_routed_owner_request" }, true);
        }
        for (const key of tokenState.keys ?? executionKeys) browserOpenExecutionTokens.delete(key);
        const url = tokenState.url;
        const result = await runProcess("/usr/bin/open", ["-a", "Google Chrome", url], {
          timeoutMs: 10_000,
        });
        if (result.code !== 0) {
          const fallback = await runProcess("/usr/bin/open", [url], { timeoutMs: 10_000 });
          return toolText(
            {
              ok: fallback.code === 0,
              url,
              browser: "default",
              stdout: fallback.stdout,
              stderr: fallback.stderr,
            },
            fallback.code !== 0,
          );
        }
        return toolText({ ok: true, url, browser: "Google Chrome" });
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  }));
  api.registerTool((toolContext = {}) => ({
    name: "harness_screen_inspect",
    description:
      "Inspect the currently visible Mac GUI screen through the OpenClaw Peekaboo bridge. Use for owner requests asking what is visible on the current screen or browser window. Fails fast when the GUI bridge socket or macOS Screen Recording/Accessibility permissions are missing.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        question: {
          type: "string",
          maxLength: 500,
          default: "Describe the currently visible screen briefly.",
        },
      },
    },
    async execute(toolCallId, params) {
      try {
        const executionKeys = screenInspectExecutionKeys({ toolCallId, id: toolCallId }, toolContext);
        const tokenState = executionKeys
          .map((key) => screenInspectExecutionTokens.get(key))
          .find((state) => state && state.expiresAt > Date.now());
        if (!tokenState || tokenState.expiresAt <= Date.now()) {
          for (const key of executionKeys) screenInspectExecutionTokens.delete(key);
          return toolText({ ok: false, error: "screen_inspect_not_bound_to_routed_owner_request" }, true);
        }
        for (const key of tokenState.keys ?? executionKeys) screenInspectExecutionTokens.delete(key);
        const result = await inspectMacScreen({
          question: tokenState.question || params?.question,
        });
        if (
          result.ok &&
          /(?:쿠팡|coupang)/i.test(tokenState.question ?? "") &&
          isOwnerOnlyDiscordSession(
            toolContext.sessionKey,
            api.config,
            pluginOwnerSenderIds,
          )
        ) {
          try {
            result.evidenceDelivery = await deliverOwnerScreenEvidence(
              toolContext.sessionKey,
              result,
            );
          } catch {
            result.evidenceDelivery = {
              attempted: true,
              ok: false,
              error: "evidence_delivery_failed",
            };
          }
        }
        if (tokenState.runState) tokenState.runState.result = result;
        return toolText(result, !result.ok);
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  }));
  api.registerTool((toolContext = {}) => ({
    name: "harness_coupang_product_detail_open",
    description:
      "Open exactly one visible Coupang search-result product detail page by clicking the OCR-matched product card. Owner-gated. It never logs in, adds to cart, buys, pays, or submits forms.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        productNameTerms: {
          type: "array",
          items: { type: "string", minLength: 1, maxLength: 80 },
          maxItems: 6,
          default: [],
          description: "Required product-name terms that must all appear in the same visible product card.",
        },
        price: {
          type: "string",
          maxLength: 40,
          default: "",
          description: "Optional visible product price such as 70,000원.",
        },
      },
    },
    async execute(toolCallId, params) {
      try {
        const executionKeys = coupangDetailOpenExecutionKeys({ toolCallId, id: toolCallId }, toolContext);
        const tokenState = executionKeys
          .map((key) => coupangDetailOpenExecutionTokens.get(key))
          .find((state) => state && state.expiresAt > Date.now());
        if (!tokenState || tokenState.expiresAt <= Date.now()) {
          for (const key of executionKeys) coupangDetailOpenExecutionTokens.delete(key);
          return toolText({ ok: false, error: "coupang_detail_open_not_bound_to_routed_owner_request" }, true);
        }
        for (const key of tokenState.keys ?? executionKeys) coupangDetailOpenExecutionTokens.delete(key);
        const result = await openCoupangProductDetail({
          productNameTerms: params?.productNameTerms ?? tokenState.productNameTerms,
          price: params?.price ?? tokenState.price,
        });
        return toolText(result, !result.ok);
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  }));
  api.registerTool((toolContext = {}) => ({
    name: "harness_notion_archive_create",
    description:
      "Create one internal Harness operating record in the configured Notion archive. Use when the owner explicitly asks to record, save, register, or archive content in Notion. Return the real page ID and URL; never use ChatGPT plugin installation state for this path.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: ["title", "body"],
      properties: {
        title: { type: "string", minLength: 1, maxLength: 200 },
        body: { type: "string", minLength: 1, maxLength: 20000 },
        artifactType: { type: "string", default: "ops_brief" },
        teams: { type: "array", maxItems: 5, items: { type: "string" }, default: ["Chief of Staff"] },
        project: { type: "string", default: "Harness Platform" },
        sourceChannel: { type: "string", default: "Discord" },
        eventDate: { type: "string" },
        reminderDate: { type: "string" },
        canonicalKey: { type: "string" },
        summary: { type: "string", maxLength: 1900 },
        decisionSummary: { type: "string", maxLength: 1900 },
        actionItems: { type: "string", maxLength: 1900 },
        historicalValue: { type: "string", default: "high" },
        tags: { type: "array", maxItems: 10, items: { type: "string" } },
      },
    },
    async execute(_id, params) {
      try {
        const trustedOwner =
          toolContext.senderIsOwner === true ||
          (toolContext.requesterSenderId &&
            configuredOwnerSenderIds().has(String(toolContext.requesterSenderId))) ||
          [toolContext.sessionKey, toolContext.sessionId]
            .filter(Boolean)
            .map(String)
            .some((key) => pluginOwnerSessionKeys.has(key));
        if (!trustedOwner) {
          return toolText({ ok: false, error: "notion_write_not_bound_to_owner_request" }, true);
        }
        const result = await runProcess(
          python(),
          ["-m", "scripts.openclaw_notion_archive"],
          { cwd: harnessRepoRoot(), timeoutMs: 60_000, stdin: JSON.stringify(params) },
        );
        return toolText(result.stdout || result.stderr, result.code !== 0);
      } catch (error) {
        return toolText({ ok: false, error: error.message }, true);
      }
    },
  }), { name: "harness_notion_archive_create" });
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

export function shouldEnforceSajuNotebookStatus(prompt) {
  const text = String(prompt ?? "");
  return (
    SAJU_MARKERS.test(text) &&
    SAJU_NOTEBOOK_STATUS_INTENT.test(text) &&
    !SAJU_NOTEBOOK_STATUS_EXCLUDED_INTENT.test(text)
  );
}

export function sajuNotebookStatusSearchTerm(prompt) {
  const text = String(prompt ?? "");
  return SAJU_NOTEBOOK_SEARCH_TERMS.find((term) => text.includes(term)) ?? "";
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

const SAJU_QUERY_TIMEOUT_SECONDS = 300;
const SAJU_BRIDGE_TIMEOUT_MS = (SAJU_QUERY_TIMEOUT_SECONDS + 30) * 1000;

export function sajuBridgeErrorCode(error) {
  const message = error instanceof Error ? error.message : String(error);
  if (/timed out/i.test(message)) return "bridge_timeout";
  if (/not found|trustedRepo|repository root/i.test(message)) return "bridge_unavailable";
  if (/output exceeded/i.test(message)) return "output_limit_exceeded";
  return "bridge_execution_failed";
}

export function runSajuBridge(question, timeoutMs = SAJU_BRIDGE_TIMEOUT_MS) {
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
        String(SAJU_QUERY_TIMEOUT_SECONDS),
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
      finish(() => reject(new Error(`Saju bridge timed out after ${timeoutMs}ms`)));
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

export async function runSajuNotebookStatus(search = "") {
  const repo = path.join(process.env.HOME ?? "", "projects", "harness-platform");
  const trustedRepo =
    [
      ".git",
      ".venv/bin/python",
      "scripts/openclaw_codex_bridge.py",
    ].every((required) => fs.existsSync(path.join(repo, required)));
  if (!trustedRepo) throw new Error("Harness repository root was not found");
  const args = [
    path.join(repo, "scripts", "openclaw_codex_bridge.py"),
    "saju-notebook-sources",
    "--format",
    "json",
  ];
  const query = String(search ?? "").trim();
  if (query) args.push("--search", query);
  const result = await runProcess(path.join(repo, ".venv", "bin", "python"), args, {
    cwd: repo,
    timeoutMs: 45_000,
  });
  if (result.code !== 0) {
    throw new Error(`Saju notebook status failed with exit code ${result.code}: ${result.stderr.slice(0, 300)}`);
  }
  return result.stdout;
}

export default {
  id: "harness-bridge",
  name: "Harness Bridge",
  description: "Harness OpenClaw command bundle for the Codex bridge",
  register(api) {
    pluginOwnerSenderIds = new Set(
      Array.isArray(api.pluginConfig?.ownerSenderIds)
        ? api.pluginConfig.ownerSenderIds.map(String).filter(Boolean)
        : [],
    );
    pluginOwnerSessionKeys = new Set(
      Array.isArray(api.pluginConfig?.ownerSessionKeys)
        ? api.pluginConfig.ownerSessionKeys
            .map(String)
            .filter((sessionKey) =>
              isOwnerOnlyDiscordSession(sessionKey, api.config, pluginOwnerSenderIds),
            )
        : [],
    );
    registerHarnessWorkspaceTools(api);
    registerHarnessAssistantTools(api);
    const activeSajuRuns = new Map();
    const activeKnowledgeRuns = new Map();
    const activeCopilotUsageRuns = new Map();
    const activeBrowserOpenRuns = new Map();
    const activeScreenInspectRuns = new Map();
    const activeCoupangDetailOpenRuns = new Map();
    const activePumpRuns = new Map();
    const pendingPumpRequests = new Map();
    const pendingCoupangEvidenceReplies = new Map();
    const pendingCoupangEvidenceSessions = new Map();
    const dispatchedCoupangEvidenceSessions = new Map();
    const activeVerificationRuns = new Map();
    const pendingVerificationReplies = new Map();
    const pendingVerificationSessions = new Map();
    const dispatchedVerificationSessions = new Map();
    const evidenceSessionKey = (event = {}, context = {}) =>
      String(event.sessionKey ?? context.sessionKey ?? context.sessionId ?? "");
    const pendingEvidenceKeys = (event = {}, context = {}) => {
      const runId = String(event.runId ?? context.runId ?? "");
      const sessionKey = evidenceSessionKey(event, context);
      if (!sessionKey) return [];
      if (
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
          runId,
        )
      ) {
        return [`${sessionKey}:${runId}`];
      }
      return [];
    };
    const pendingStateFor = (map, sessions, event, context) => {
      for (const key of pendingEvidenceKeys(event, context)) {
        const state = map.get(key);
        if (state) return state;
      }
      const queue = sessions.get(evidenceSessionKey(event, context)) ?? [];
      return queue.length === 1 ? queue[0] : undefined;
    };
    const dispatchedEvidenceKey = (event = {}, context = {}) => {
      const sessionKey = evidenceSessionKey(event, context);
      const content = String(event.content ?? event.payload?.text ?? "");
      if (!sessionKey || !content) return "";
      return `${sessionKey}:${crypto.createHash("sha256").update(content).digest("hex")}`;
    };
    const enqueuePendingState = (sessions, sessionKey, state) => {
      const queue = sessions.get(sessionKey) ?? [];
      if (queue.at(-1) !== state) queue.push(state);
      sessions.set(sessionKey, queue);
    };
    const deleteSessionState = (sessions, state) => {
      const sessionKey = state?.sessionKey;
      const queue = sessions.get(sessionKey);
      if (!queue) return;
      const remaining = queue.filter((candidate) => candidate !== state);
      if (remaining.length > 0) sessions.set(sessionKey, remaining);
      else sessions.delete(sessionKey);
    };
    const deleteStateFromAllQueues = (queues, state) => {
      for (const [key, queue] of queues) {
        const remaining = queue.filter((candidate) => candidate !== state);
        if (remaining.length > 0) queues.set(key, remaining);
        else queues.delete(key);
      }
    };
    const pruneExpiredQueuedStates = (queues, now) => {
      for (const [key, queue] of queues) {
        const active = queue.filter((state) => state?.expiresAt > now);
        if (active.length > 0) queues.set(key, active);
        else queues.delete(key);
      }
    };
    const deletePendingState = (map, sessions, state) => {
      for (const key of state?.evidenceKeys ?? []) {
        if (map.get(key) === state) map.delete(key);
      }
      deleteSessionState(sessions, state);
    };
    const schedulePendingCaptureCleanup = (state) => {
      const delayMs = Math.max(1_000, state.expiresAt - Date.now() + 1_000);
      const timer = setTimeout(() => {
        if (
          !pendingCoupangEvidenceSessions
            .get(state.sessionKey)
            ?.some((candidate) => candidate === state)
        ) {
          return;
        }
        for (const imagePath of state.mediaPaths ?? []) {
          try {
            const moved = moveDisposableCaptureToTrash(
              imagePath,
              state.mediaIdentities?.[imagePath],
            );
            if (!moved) api.logger?.warn?.("peekaboo capture expiry cleanup was not applied");
          } catch (error) {
            api.logger?.warn?.(`peekaboo capture expiry cleanup failed: ${error.message}`);
          }
        }
        deletePendingState(
          pendingCoupangEvidenceReplies,
          pendingCoupangEvidenceSessions,
          state,
        );
        deleteStateFromAllQueues(dispatchedCoupangEvidenceSessions, state);
      }, delayMs);
      state.cleanupTimer = timer;
      timer.unref?.();
    };
    const schedulePendingVerificationCleanup = (state) => {
      const timer = setTimeout(() => {
        if (
          pendingVerificationSessions
            .get(state.sessionKey)
            ?.some((candidate) => candidate === state)
        ) {
          deletePendingState(
            pendingVerificationReplies,
            pendingVerificationSessions,
            state,
          );
          deleteStateFromAllQueues(dispatchedVerificationSessions, state);
        }
      }, Math.max(1_000, state.expiresAt - Date.now() + 1_000));
      state.cleanupTimer = timer;
      timer.unref?.();
    };
    const runKeys = (event = {}, context = {}) =>
      [event.runId, context.runId, context.sessionKey, context.sessionId]
        .filter(Boolean)
        .map(String);
    const copilotRunKeys = (event = {}, context = {}) =>
      [event.runId, context.runId].filter(Boolean).map(String);
    const pruneRuns = () => {
      const now = Date.now();
      for (const [key, expiresAt] of activeSajuRuns) {
        if (expiresAt <= now) activeSajuRuns.delete(key);
      }
      for (const [key, state] of activeKnowledgeRuns) {
        if (state.expiresAt <= now) activeKnowledgeRuns.delete(key);
      }
      for (const [key, expiresAt] of activeCopilotUsageRuns) {
        if (expiresAt <= now) activeCopilotUsageRuns.delete(key);
      }
      for (const [key, state] of activeBrowserOpenRuns) {
        if (state.expiresAt <= now) activeBrowserOpenRuns.delete(key);
      }
      for (const [key, state] of activeScreenInspectRuns) {
        if (state.expiresAt <= now) activeScreenInspectRuns.delete(key);
      }
      for (const [key, state] of activeCoupangDetailOpenRuns) {
        if (state.expiresAt <= now) activeCoupangDetailOpenRuns.delete(key);
      }
      for (const [key, state] of browserOpenExecutionTokens) {
        if (state.expiresAt <= now) browserOpenExecutionTokens.delete(key);
      }
      for (const [key, state] of screenInspectExecutionTokens) {
        if (state.expiresAt <= now) screenInspectExecutionTokens.delete(key);
      }
      for (const [key, state] of activePumpRuns) {
        if (state.expiresAt <= now) activePumpRuns.delete(key);
      }
      for (const [key, state] of pendingPumpRequests) {
        if (state.expiresAt <= now) pendingPumpRequests.delete(key);
      }
      for (const [key, state] of pendingCoupangEvidenceReplies) {
        if (state.expiresAt > now) continue;
        if (state.cleanupTimer) clearTimeout(state.cleanupTimer);
        for (const imagePath of state.mediaPaths ?? []) {
          try {
            const moved = moveDisposableCaptureToTrash(
              imagePath,
              state.mediaIdentities?.[imagePath],
            );
            if (!moved) api.logger?.warn?.("peekaboo capture prune cleanup was not applied");
          } catch (error) {
            api.logger?.warn?.(`peekaboo capture prune cleanup failed: ${error.message}`);
          }
        }
        pendingCoupangEvidenceReplies.delete(key);
      }
      for (const [key, state] of activeVerificationRuns) {
        if (state.expiresAt <= now) activeVerificationRuns.delete(key);
      }
      for (const [key, state] of pendingVerificationReplies) {
        if (state.expiresAt <= now) pendingVerificationReplies.delete(key);
      }
      pruneExpiredQueuedStates(pendingCoupangEvidenceSessions, now);
      pruneExpiredQueuedStates(dispatchedCoupangEvidenceSessions, now);
      pruneExpiredQueuedStates(pendingVerificationSessions, now);
      pruneExpiredQueuedStates(dispatchedVerificationSessions, now);
      while (activeSajuRuns.size > 1024) {
        activeSajuRuns.delete(activeSajuRuns.keys().next().value);
      }
      while (activeKnowledgeRuns.size > 1024) {
        activeKnowledgeRuns.delete(activeKnowledgeRuns.keys().next().value);
      }
      while (activeCopilotUsageRuns.size > 1024) {
        activeCopilotUsageRuns.delete(activeCopilotUsageRuns.keys().next().value);
      }
      while (activeBrowserOpenRuns.size > 1024) {
        activeBrowserOpenRuns.delete(activeBrowserOpenRuns.keys().next().value);
      }
      while (activeScreenInspectRuns.size > 1024) {
        activeScreenInspectRuns.delete(activeScreenInspectRuns.keys().next().value);
      }
      while (browserOpenExecutionTokens.size > 1024) {
        browserOpenExecutionTokens.delete(browserOpenExecutionTokens.keys().next().value);
      }
      while (screenInspectExecutionTokens.size > 1024) {
        screenInspectExecutionTokens.delete(screenInspectExecutionTokens.keys().next().value);
      }
      while (coupangDetailOpenExecutionTokens.size > 1024) {
        coupangDetailOpenExecutionTokens.delete(coupangDetailOpenExecutionTokens.keys().next().value);
      }
      while (activeCoupangDetailOpenRuns.size > 1024) {
        activeCoupangDetailOpenRuns.delete(activeCoupangDetailOpenRuns.keys().next().value);
      }
      while (activePumpRuns.size > 1024) {
        activePumpRuns.delete(activePumpRuns.keys().next().value);
      }
      while (pendingPumpRequests.size > 1024) {
        pendingPumpRequests.delete(pendingPumpRequests.keys().next().value);
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
    const markKnowledgeRun = (event, context) => {
      pruneRuns();
      const state = {
        expiresAt: Date.now() + 10 * 60_000,
        queryCalls: 0,
        question: String(event.prompt ?? ""),
      };
      for (const key of runKeys(event, context)) activeKnowledgeRuns.set(key, state);
    };
    const knowledgeRunState = (event, context) => {
      pruneRuns();
      for (const key of runKeys(event, context)) {
        const state = activeKnowledgeRuns.get(key);
        if (state) return state;
      }
      return undefined;
    };
    const clearKnowledgeRun = (event, context) => {
      for (const key of runKeys(event, context)) activeKnowledgeRuns.delete(key);
    };
    const markCopilotUsageRun = (event, context) => {
      pruneRuns();
      const expiresAt = Date.now() + 10 * 60_000;
      for (const key of copilotRunKeys(event, context)) activeCopilotUsageRuns.set(key, expiresAt);
    };
    const isCopilotUsageRun = (event, context) => {
      pruneRuns();
      return copilotRunKeys(event, context).some((key) => activeCopilotUsageRuns.has(key));
    };
    const clearCopilotUsageRun = (event, context) => {
      for (const key of copilotRunKeys(event, context)) activeCopilotUsageRuns.delete(key);
    };
    const browserRunKeys = (event = {}, context = {}) =>
      [event.runId, context.runId].filter(Boolean).map(String);
    const screenInspectRunKeys = (event = {}, context = {}) =>
      [
        event.runId,
        context.runId,
        event.sessionKey,
        context.sessionKey,
        event.sessionId,
        context.sessionId,
      ]
        .filter(Boolean)
        .map(String);
    const verificationRunState = (event, context) => {
      pruneRuns();
      for (const key of browserRunKeys(event, context)) {
        const state = activeVerificationRuns.get(key);
        if (state) return state;
      }
      return undefined;
    };
    const markVerificationRun = (event, context) => {
      const state = {
        expiresAt: Date.now() + 10 * 60_000,
        question: currentUserInstruction(event.prompt),
        toolResults: [],
        finalizeAttempts: 0,
      };
      const keys = browserRunKeys(event, context);
      for (const key of keys) activeVerificationRuns.set(key, state);
      const timer = setTimeout(() => {
        for (const key of keys) {
          if (activeVerificationRuns.get(key) === state) activeVerificationRuns.delete(key);
        }
      }, 10 * 60_000 + 1_000);
      timer.unref?.();
    };
    const clearVerificationRun = (event, context) => {
      for (const key of browserRunKeys(event, context)) activeVerificationRuns.delete(key);
    };
    const markBrowserOpenRun = (event, context) => {
      pruneRuns();
      const state = {
        expiresAt: Date.now() + 3 * 60_000,
        expectedUrl: browserOpenTargetFromPrompt(event.prompt),
        called: false,
      };
      for (const key of browserRunKeys(event, context)) activeBrowserOpenRuns.set(key, state);
    };
    const browserOpenRunState = (event, context) => {
      pruneRuns();
      for (const key of browserRunKeys(event, context)) {
        const state = activeBrowserOpenRuns.get(key);
        if (state) return state;
      }
      return undefined;
    };
    const clearBrowserOpenRun = (event, context) => {
      for (const key of browserRunKeys(event, context)) activeBrowserOpenRuns.delete(key);
    };
    const markScreenInspectRun = (event, context) => {
      pruneRuns();
      const question = currentUserInstruction(event.prompt);
      const contextualQuestion =
        SCREEN_INSPECT_DETAIL_FOLLOWUP_REQUEST.test(question)
          ? `직전 화면판독 문맥의 쿠팡/Chrome 화면에서 ${question}`
          : question;
      const state = {
        expiresAt: Date.now() + 3 * 60_000,
        question: contextualQuestion,
        called: false,
      };
      for (const key of screenInspectRunKeys(event, context)) activeScreenInspectRuns.set(key, state);
    };
    const screenInspectRunState = (event, context) => {
      pruneRuns();
      for (const key of screenInspectRunKeys(event, context)) {
        const state = activeScreenInspectRuns.get(key);
        if (state) return state;
      }
      return undefined;
    };
    const clearScreenInspectRun = (event, context) => {
      const states = new Set(
        screenInspectRunKeys(event, context)
          .map((key) => activeScreenInspectRuns.get(key))
          .filter(Boolean),
      );
      for (const [key, token] of screenInspectExecutionTokens) {
        if (states.has(token.runState)) screenInspectExecutionTokens.delete(key);
      }
      for (const key of screenInspectRunKeys(event, context)) activeScreenInspectRuns.delete(key);
    };
    const markCoupangDetailOpenRun = (event, context) => {
      pruneRuns();
      const question = currentUserInstruction(event.prompt);
      const state = {
        expiresAt: Date.now() + 3 * 60_000,
        productNameTerms: productSearchTermsFromQuestion(question),
        price: firstPriceString(question) ?? "",
        called: false,
      };
      for (const key of browserRunKeys(event, context)) activeCoupangDetailOpenRuns.set(key, state);
    };
    const coupangDetailOpenRunState = (event, context) => {
      pruneRuns();
      for (const key of browserRunKeys(event, context)) {
        const state = activeCoupangDetailOpenRuns.get(key);
        if (state) return state;
      }
      return undefined;
    };
    const clearCoupangDetailOpenRun = (event, context) => {
      for (const key of browserRunKeys(event, context)) activeCoupangDetailOpenRuns.delete(key);
    };
    const pumpRunKeys = (event = {}, context = {}) =>
      [event.runId, context.runId].filter(Boolean).map(String);
    const markPumpRun = (event, context, intent) => {
      pruneRuns();
      const state = { ...intent, expiresAt: Date.now() + 3 * 60_000 };
      for (const key of pumpRunKeys(event, context)) activePumpRuns.set(key, state);
    };
    const pumpRunState = (event, context) => {
      pruneRuns();
      for (const key of pumpRunKeys(event, context)) {
        const state = activePumpRuns.get(key);
        if (state) return state;
      }
      return undefined;
    };
    const clearPumpRun = (event, context) => {
      for (const key of pumpRunKeys(event, context)) activePumpRuns.delete(key);
    };
    const pumpConversationKey = (context, senderId) => {
      const conversation = context?.sessionKey ?? context?.sessionId;
      return conversation && senderId ? `${conversation}:${senderId}` : undefined;
    };
    api.registerTool({
      name: "harness_saju_notebook_status",
      description:
        "Verify the fixed Saju NotebookLM source list and search recently added source titles. Use for source/addition/status checks, not fortune interpretation.",
      parameters: {
        type: "object",
        additionalProperties: false,
        required: [],
        properties: {
          search: {
            type: "string",
            description: "Optional source-title or URL keyword to match, e.g. 대운.",
            maxLength: 200,
          },
        },
      },
      async execute(_toolCallId, params) {
        try {
          const output = await runSajuNotebookStatus(params.search || "");
          return { content: [{ type: "text", text: output }] };
        } catch (error) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  ok: false,
                  error: "saju_notebook_status_failed",
                  reason: sajuBridgeErrorCode(error),
                }),
              },
            ],
            isError: true,
          };
        }
      },
    });
    api.registerTool({
      name: "harness_saju_query",
      description:
        "Query the fixed Saju NotebookLM through deterministic dates, expert validation, private cache, and compact relay. Also returns source status for Saju NotebookLM material-addition checks.",
      parameters: {
        type: "object",
        additionalProperties: false,
        required: ["question", "timeoutSeconds"],
        properties: {
          question: {
            type: "string",
            description:
              "Self-contained question with explicit birth date/time and target date reconstructed from conversation.",
            minLength: 1,
            maxLength: 4000,
          },
          timeoutSeconds: {
            type: "integer",
            const: SAJU_QUERY_TIMEOUT_SECONDS,
            description: "Required OpenClaw dynamic-tool timeout override. Always pass 300.",
          },
        },
      },
      async execute(_toolCallId, params) {
        try {
          if (shouldEnforceSajuNotebookStatus(params.question)) {
            const search = sajuNotebookStatusSearchTerm(params.question);
            const output = await runSajuNotebookStatus(search);
            return { content: [{ type: "text", text: output }] };
          }
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
                  reason: sajuBridgeErrorCode(error),
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
        pruneRuns();
        const senderId = currentSenderId(event.prompt);
        const pendingKey = pumpConversationKey(context, senderId);
        const pending = pendingKey ? pendingPumpRequests.get(pendingKey) : undefined;
        const actuatorConversation =
          Boolean(senderId) && (SMARTFARM_PUMP_CONTEXT.test(String(event.prompt ?? "")) || pending);
        if (actuatorConversation) {
          markPumpRun(event, context, {
            senderId,
            pendingKey,
            pending,
            confirmed: true,
          });
          return {
            appendSystemContext: [
              "[SMARTFARM PUMP CONTROL — MANDATORY]",
              "Understand the user's actuator intent semantically from the full conversation; do not match a fixed phrase or require a fixed word order.",
              `The server-side pending request is ${JSON.stringify(pending ?? {})}.`,
              "For every actuator request or follow-up, call harness_smartfarm_pump_control exactly once with every zone/action value you can infer confidently; omit fields that are genuinely missing.",
              "The tool owns missing-field state and user/channel binding. Relay its missingFields question or final safety result.",
              "Never use bash, exec, shell, mosquitto_pub, or another actuator path. Never wait for a second OpenClaw internal approval.",
            ].join(" "),
          };
        }
        const requestText = currentUserInstruction(event.prompt);
        const notionArchiveRequest =
          currentSenderIsOwner(event.prompt, context, event) &&
          NOTION_ARCHIVE_REQUEST.test(requestText);
        if (notionArchiveRequest) {
          return {
            appendSystemContext: [
              "[HARNESS NOTION ARCHIVE — MANDATORY]",
              "The owner explicitly requested a Notion write in this turn.",
              "Call `harness_notion_archive_create` exactly once with a concise title and the complete requested record.",
              "Use the configured Harness Notion API path. Never inspect, install, suggest, or report the ChatGPT Notion app/plugin.",
              "Claim success only from the returned real page_id and url.",
            ].join(" "),
          };
        }
        const ownerRequest = currentSenderIsOwner(event.prompt, context, event);
        if (ownerRequest && shouldEnforceVerificationEvidence(requestText)) {
          markVerificationRun(event, context);
        }
        const browserOpenRequest = ownerRequest && shouldEnforceBrowserOpen(event.prompt);
        const screenInspectRequest =
          ownerRequest && shouldEnforceScreenInspect(event.prompt, event.messages, context);
        const coupangDetailOpenRequest =
          ownerRequest &&
          COUPANG_DETAIL_OPEN_REQUEST.test(requestText) &&
          !HIGH_IMPACT_BROWSER_ACTION.test(requestText) &&
          hasRecentScreenInspectTrajectory(context);
        if (coupangDetailOpenRequest) {
          markCoupangDetailOpenRun(event, context);
          markScreenInspectRun(event, context);
          return {
            appendSystemContext: [
              "[HARNESS COUPANG PRODUCT DETAIL OPEN + SCREEN INSPECT — MANDATORY]",
              "The owner asked to open a visible Coupang product detail page and report details.",
              "First call `harness_coupang_product_detail_open` exactly once. Pass every product-name term known from the current or immediately previous user/product answer context, and pass the referenced price if present.",
              "Then call `harness_screen_inspect` exactly once to read the opened detail page.",
              "Do not use shell, Peekaboo CLI, Playwright, Browser MCP, web_fetch, browser-fill, login, cart, checkout, payment, purchase, or form actions.",
              "If the detail-open tool cannot find an exact visible product card, report that exact blocker; do not click another product or guess.",
            ].join(" "),
          };
        }
        if (browserOpenRequest && screenInspectRequest) {
          markBrowserOpenRun(event, context);
          markScreenInspectRun(event, context);
          const targetUrl = browserOpenTargetFromPrompt(event.prompt) ?? "https://www.coupang.com/";
          const isCoupangSearch =
            COUPANG_SEARCH_REQUEST.test(requestText) ||
            COUPANG_PRODUCT_EVIDENCE_REQUEST.test(requestText);
          return {
            appendSystemContext: [
              "[HARNESS BROWSER OPEN + SCREEN INSPECT — MANDATORY]",
              "The owner asked to open a Mac GUI browser page and then report what is visible.",
              `First call \`harness_browser_open\` exactly once with url ${targetUrl}.`,
              "Then call `harness_screen_inspect` exactly once with the current user question, including any read-only login-status question.",
              ...(isCoupangSearch
                ? [
                    "For Coupang product search or price questions, answer from `result.smart_collection.merged.strict_product_matches` when it is non-empty.",
                    "A strict product match means every meaningful search term appears inside the same OCR product-card cluster. Do not combine `price_candidates` from a different item with a product name.",
                    "If multiple strict_product_matches are present, enumerate every match unless the owner explicitly asks for only the cheapest, first, or one selected product.",
                    "If strict_product_matches is empty, say that no exact all-term product match was confirmed instead of guessing from loose OCR candidates.",
                    "Every reported price must occur in that matching card's own `current_price_candidates`. Never answer a price from web search, memory, page-wide OCR, or a neighboring card.",
                    "State the evidence mode as `현재 쿠팡 화면 OCR`. Do not say `웹 인덱스`, `체감 판매가`, or `대략`.",
                  ]
                : []),
              "Do not use shell, Peekaboo CLI, Playwright, Browser MCP, screenshots, web_search, web_fetch, browser-fill, coupang-cart, login, checkout, payment, or any form action for this request.",
              "Report success only from the two Harness tool results. If screen inspection reports missing bridge socket or macOS permissions, answer with that exact operational blocker.",
            ].join(" "),
          };
        }
        if (browserOpenRequest) {
          markBrowserOpenRun(event, context);
          const targetUrl = browserOpenTargetFromPrompt(event.prompt) ?? "https://www.coupang.com/";
          return {
            appendSystemContext: [
              "[HARNESS BROWSER OPEN — MANDATORY]",
              "The user asked to open a browser page in the Mac GUI.",
              `Call \`harness_browser_open\` exactly once with url ${targetUrl}.`,
              "Do not use shell, Playwright, Browser MCP, browser-fill, coupang-cart, login, checkout, payment, or any form action for this request.",
              "Report success only from the tool result.",
            ].join(" "),
          };
        }
        if (screenInspectRequest) {
          markScreenInspectRun(event, context);
          return {
            appendSystemContext: [
              "[HARNESS SCREEN INSPECT — MANDATORY]",
              "The user asked what is currently visible on the Mac GUI screen or browser window.",
              "Call `harness_screen_inspect` exactly once with the current user question.",
              "Do not use shell, Peekaboo CLI, Playwright, Browser MCP, screenshots, or browser automation directly for this request.",
              "If the tool reports missing bridge socket or macOS permissions, answer with that exact operational blocker instead of waiting or guessing.",
            ].join(" "),
          };
        }
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
        if (shouldEnforceCopilotUsage(event.prompt)) {
          markCopilotUsageRun(event, context);
          return {
            appendSystemContext: [
              "[COPILOT USAGE ROUTING — MANDATORY]",
              "For GitHub Copilot billing, Premium Request, budget, model, session, or usage-cause questions,",
              "call `harness_copilot_usage` exactly once before answering.",
              "Answer from its aggregate snapshot. If `observed_origin.confidence` is `high`, state the observed client, producer, and repository directly; if it is `partial`, state only the supported breakdown and its limits.",
              "When confidence is high, do not weaken the known local attribution into 'unknown client'. Scope it precisely to locally recorded Copilot CLI sessions; it does not observe IDE, web, or another machine.",
              "Always distinguish local attribution from GitHub billed-unit identity.",
              "Never use bash, exec, shell, memory, or workspace search for this intent.",
              "Do not claim the snapshot maps an individual GitHub billed request to an individual prompt.",
            ].join(" "),
          };
        }
        if (
          shouldEnforceHarnessKnowledge(event.prompt) &&
          !shouldEnforceSajuBridge(event.prompt, event.messages)
        ) {
          markKnowledgeRun(event, context);
          return {
            appendSystemContext: [
              "[HARNESS KNOWLEDGE ROUTING — MANDATORY]",
              "For any Harness business, program, policy, implementation, or status question,",
              "call `harness_knowledge_query` first with the complete user question.",
              "After its first successful result, answer immediately from `domainEvidence` and `evidence`.",
              "Do not call `harness_workspace_search`, shell, or the knowledge tool again.",
              "Cite as plain backticked `repository/relative/path:line` text.",
              "Never invent an absolute path or Markdown file link.",
              "Separate repository knowledge from live runtime/external state.",
              "Call `harness_alpaca_status` only when the user explicitly requests live account, position, order, signal, or KPI state.",
            ].join(" "),
          };
        }
        if (!shouldEnforceSajuBridge(event.prompt, event.messages)) {
          return;
        }
        if (shouldEnforceSajuNotebookStatus(event.prompt)) {
          return {
            appendSystemContext: [
              "[HARNESS SAJU NOTEBOOK STATUS — MANDATORY]",
              "The user asked whether sources or research material were added to the fixed Saju NotebookLM.",
              "Call `harness_saju_notebook_status` exactly once. Use `search` for the requested topic if present, for example `대운`.",
              "If `harness_saju_notebook_status` is not visible in the current tool list, call `harness_saju_query` exactly once with the original status-check question; the bridge will return source status instead of running a fortune query.",
              "Answer only from the returned source_count, updated_at, match_count, and matches.",
              "Do not call NotebookLM query/chat, nlm directly, shell, or workspace search for this status check.",
            ].join(" "),
          };
        }
        markSajuRun(event, context);
        return {
          appendSystemContext: [
            "[HARNESS SAJU ROUTING — MANDATORY]",
            "For any Saju/명리/일진/운세 request and its contextual follow-ups,",
            "NEVER run `nlm notebook query`, NotebookLM MCP query, or nlm-skill directly.",
            "Reconstruct omitted birth/target dates and birth time from recent conversation,",
            "then call only the `harness_saju_query` tool. For daily fortune and every other person's Saju question, include that the answer must consider 10-year 대운 as the long-term layer.",
            "Send delivery_text verbatim only when the user did not request a specific length, sentence count, structure, or reading level.",
            "When the user requests an output format, rewrite delivery_text to that format while preserving its dates, factual basis, uncertainty, and safety cautions; do not copy the long expert report verbatim.",
            "For a requested 8-to-12-sentence easy-language daily briefing, output exactly 8 to 12 Korean sentences, omit the raw chart and citation inventory, and keep the 10-year 대운, year, month, day, practical cautions, both a labeled good time window and a labeled avoid time window with one plain-language reason each, and final action advice.",
            "Use these exact templates once each: `좋은 시간대:HH:MM~HH:MM - 쉬운 이유 한 문장` and `피할 시간대:HH:MM~HH:MM - 쉬운 이유 한 문장`; never omit either window.",
            "Use everyday Korean first; do not use unexplained terms such as 십신, 식상, 재성, 편관, 칠살, 형살, 합, 충, 극, or 지지, and if one traditional name is necessary put it once in parentheses after the plain explanation.",
            "Split the briefing into short paragraphs of 2 to 3 sentences with blank lines, and put each time-window label in its own paragraph; never send all sentences as one dense paragraph.",
            "Limit the unchanged 10-year, yearly, and monthly background to at most 3 sentences total, then explicitly state 1 or 2 ways today's daily layer differs from that background so consecutive briefings do not repeat generic cautions as if they were new.",
            "Use the bridge result's `daily_history.comparison_available` and grounded delivery_text. Add exactly one `전날 대비:` sentence: preserve its grounded comparison of yesterday and today; only say `비교 자료 부족` when comparison_available is false.",
            "Add exactly one `오늘 시간 흐름:` sentence preserving the grounded morning-to-afternoon-to-evening rise, peak, easing, or flat flow from delivery_text. The daily bridge contract requires all three periods; do not replace a present grounded flow with `비교 자료 부족`.",
            "Never claim a multi-day trend from repeated wording alone, and never predict tomorrow unless tomorrow was separately grounded.",
            "If the request also requires verification evidence, reserve one sentence inside that limit for the plugin evidence line so the delivered reply still totals 8 to 12 sentences.",
            "The bridge owns deterministic dates, expert contracts, privacy, and cache.",
            "If `harness_saju_query` returns `saju_bridge_failed`, do not send that failure as the final user report.",
            "Retry `harness_saju_query` with the identical arguments until it succeeds within the platform execution window, and publish only the successful grounded result.",
          ].join(" "),
        };
      },
      { priority: 1000 },
    );
    api.on(
      "before_tool_call",
      async (event, context) => {
        if (isRawPumpShellCall(event.toolName, event.params)) {
          return {
            block: true,
            blockReason:
              "Raw MQTT pump shell commands are always blocked; use harness_smartfarm_pump_control.",
          };
        }
        if (isHighImpactBrowserShellCall(event.toolName, event.params)) {
          return {
            block: true,
            blockReason:
              "High-impact browser shell commands are blocked; require a dedicated owner-gated tool and approval flow.",
          };
        }
        const pumpState = pumpRunState(event, context);
        if (event.toolName === "harness_smartfarm_pump_control") {
          if (!pumpState?.senderId || !pumpState?.pendingKey) {
            return {
              block: true,
              blockReason:
                "Smartfarm pump control requires a sender identity bound to the current conversation.",
            };
          }
          const rawZone = event.params?.zone ?? pumpState.pending?.zone;
          const zone =
            Number.isInteger(rawZone) && rawZone > 0
              ? `zone${rawZone}`
              : /^[1-9][0-9]{0,2}$/.test(String(rawZone ?? ""))
                ? `zone${rawZone}`
                : rawZone;
          const action = event.params?.action ?? pumpState.pending?.action;
          if (zone && !/^zone[1-9][0-9]{0,2}$/.test(String(zone))) {
            return { block: true, blockReason: "Invalid smartfarm zone." };
          }
          if (action && !["on", "off"].includes(String(action))) {
            return { block: true, blockReason: "Invalid smartfarm action." };
          }
          if (!zone || !action) {
            pendingPumpRequests.set(pumpState.pendingKey, {
              zone,
              action,
              expiresAt: Date.now() + 3 * 60_000,
            });
          } else {
            pendingPumpRequests.delete(pumpState.pendingKey);
          }
          return {
            params: {
              ...(zone ? { zone: String(zone) } : {}),
              ...(action ? { action: String(action) } : {}),
              durationSeconds: Math.min(
                15,
                Math.max(1, Number(event.params?.durationSeconds ?? 5)),
              ),
              dryRun: Boolean(event.params?.dryRun),
              confirmationBound: true,
            },
          };
        }
        if (pumpState && isShellTool(event.toolName)) {
          return {
            block: true,
            blockReason:
              "Raw shell actuator commands are blocked; use harness_smartfarm_pump_control after explicit confirmation.",
          };
        }
        if (event.toolName === "harness_knowledge_query") {
          const state = knowledgeRunState(event, context);
          if (state) {
            if (state.queryCalls >= 1) {
              return {
                params: {
                  ...event.params,
                  question: state.question,
                  reuseOnly: true,
                },
              };
            }
            state.queryCalls += 1;
            return {
              params: {
                ...event.params,
                question: state.question,
                reuseOnly: false,
              },
            };
          }
        }
        if (knowledgeRunState(event, context) && isKnowledgeBypassTool(event.toolName)) {
          return {
            block: true,
            blockReason:
              "Harness knowledge routing is active; call harness_knowledge_query once and answer from its canonical evidence without memory, shell, or workspace-search fallback.",
          };
        }
        if (isCopilotUsageRun(event, context) && isCopilotUsageTool(event.toolName)) {
          return;
        }
        if (isCopilotUsageRun(event, context)) {
          return {
            block: true,
            blockReason:
              "Copilot usage routing is active; call harness_copilot_usage once and answer from its aggregate snapshot.",
          };
        }
        const browserOpenState = browserOpenRunState(event, context);
        const screenInspectState = screenInspectRunState(event, context);
        const coupangDetailOpenState = coupangDetailOpenRunState(event, context);
        if (coupangDetailOpenState && isCoupangDetailOpenTool(event.toolName)) {
          const detailToolCallId = String(
            event.toolCallId ?? event.toolUseId ?? event.itemId ?? event.id ?? "",
          );
          if (coupangDetailOpenState.called) {
            if (coupangDetailOpenState.toolCallId && coupangDetailOpenState.toolCallId === detailToolCallId) {
              return;
            }
            return {
              block: true,
              blockReason: "Coupang detail-open routing already used its one allowed tool call.",
            };
          }
          coupangDetailOpenState.called = true;
          coupangDetailOpenState.toolCallId = detailToolCallId || undefined;
          const executionKeys = coupangDetailOpenExecutionKeys(event, context);
          const tokenState = {
            productNameTerms: coupangDetailOpenState.productNameTerms,
            price: coupangDetailOpenState.price,
            expiresAt: Math.min(coupangDetailOpenState.expiresAt, Date.now() + 60_000),
            keys: executionKeys,
          };
          for (const key of executionKeys) coupangDetailOpenExecutionTokens.set(key, tokenState);
          return;
        }
        if (coupangDetailOpenState && screenInspectState && isScreenInspectTool(event.toolName) && !coupangDetailOpenState.called) {
          return {
            block: true,
            blockReason:
              "Coupang detail-open plus screen-inspect routing is active; call harness_coupang_product_detail_open before harness_screen_inspect.",
          };
        }
        if (coupangDetailOpenState && !(screenInspectState && isScreenInspectTool(event.toolName))) {
          return {
            block: true,
            blockReason:
              "Coupang detail-open routing is active; call only harness_coupang_product_detail_open then harness_screen_inspect.",
          };
        }
        if (browserOpenState && isBrowserOpenTool(event.toolName)) {
          const browserToolCallId = String(
            event.toolCallId ?? event.toolUseId ?? event.itemId ?? event.id ?? "",
          );
          if (browserOpenState.called) {
            if (browserOpenState.toolCallId && browserOpenState.toolCallId === browserToolCallId) {
              return;
            }
            return {
              block: true,
              blockReason: "Browser-open routing already used its one allowed tool call.",
            };
          }
          if (!browserOpenState.expectedUrl) {
            return {
              block: true,
              blockReason: "Browser-open routing could not determine a safe URL from the user request.",
            };
          }
          let requestedUrl;
          try {
            requestedUrl = normalizeBrowserUrl(event.params?.url);
          } catch {
            return {
              block: true,
              blockReason: "Browser-open routing requires an HTTP/HTTPS URL.",
            };
          }
          if (requestedUrl !== browserOpenState.expectedUrl) {
            return {
              block: true,
              blockReason: `Browser-open routing requires url ${browserOpenState.expectedUrl}.`,
            };
          }
          browserOpenState.called = true;
          browserOpenState.toolCallId = browserToolCallId || undefined;
          const executionKeys = browserOpenExecutionKeys(event, context);
          const tokenState = {
            url: browserOpenState.expectedUrl,
            expiresAt: Math.min(browserOpenState.expiresAt, Date.now() + 60_000),
            keys: executionKeys,
          };
          for (const key of executionKeys) browserOpenExecutionTokens.set(key, tokenState);
          return;
        }
        if (browserOpenState && screenInspectState && isScreenInspectTool(event.toolName) && !browserOpenState.called) {
          return {
            block: true,
            blockReason:
              "Browser-open plus screen-inspect routing is active; call harness_browser_open before harness_screen_inspect.",
          };
        }
        if (browserOpenState && !(screenInspectState && isScreenInspectTool(event.toolName))) {
          return {
            block: true,
            blockReason:
              screenInspectState
                ? "Browser-open plus screen-inspect routing is active; call only harness_browser_open then harness_screen_inspect."
                : "Browser-open routing is active; call only harness_browser_open once.",
          };
        }
        if (screenInspectState && isScreenInspectTool(event.toolName)) {
          const screenToolCallId = String(
            event.toolCallId ?? event.toolUseId ?? event.itemId ?? event.id ?? "",
          );
          if (screenInspectState.called) {
            if (screenInspectState.toolCallId && screenInspectState.toolCallId === screenToolCallId) {
              return;
            }
            return {
              block: true,
              blockReason: "Screen-inspect routing already used its one allowed tool call.",
            };
          }
          screenInspectState.called = true;
          screenInspectState.toolCallId = screenToolCallId || undefined;
          const executionKeys = screenInspectExecutionKeys(event, context);
          const tokenState = {
            question: screenInspectState.question,
            runState: screenInspectState,
            expiresAt: Math.min(screenInspectState.expiresAt, Date.now() + 60_000),
            keys: executionKeys,
          };
          for (const key of executionKeys) screenInspectExecutionTokens.set(key, tokenState);
          return;
        }
        if (screenInspectState && (isShellTool(event.toolName) || isPeekabooShellCall(event.toolName, event.params))) {
          return {
            block: true,
            blockReason:
              "Screen-inspect routing is active; call only harness_screen_inspect once. Do not run Peekaboo through shell.",
          };
        }
        if (screenInspectState) {
          return {
            block: true,
            blockReason:
              "Screen-inspect routing is active; call only harness_screen_inspect once.",
          };
        }
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
    api.on("after_tool_call", async (event, context) => {
      const state = verificationRunState(event, context);
      if (!state) return;
      if (!verificationEvidenceToolRelevant(state.question, event.toolName)) return;
      let serialized = "";
      try {
        serialized = JSON.stringify(event.result ?? "");
      } catch {}
      const success =
        !event.error &&
        !/"ok"\s*:\s*false/i.test(serialized) &&
        !/"isError"\s*:\s*true/i.test(serialized);
      state.toolResults.push({
        toolName: String(event.toolName ?? "unknown"),
        success,
      });
    });
    api.on(
      "before_agent_finalize",
      async (event, context) => {
        const screenState = screenInspectRunState(event, context);
        const verificationState = verificationRunState(event, context);
        const runId = String(event.runId ?? context.runId ?? "");
        const evidenceKeys = pendingEvidenceKeys(event, context);
        const sessionKey = evidenceSessionKey(event, context);
        if (screenState && (!screenState.called || !screenState.result)) {
          return {
            action: "revise",
            reason: "GUI verification requires the routed screen-inspection result.",
            retry: {
              instruction:
                "Call the required harness_screen_inspect tool. If it fails, state the exact blocker. Do not substitute memory or guessed facts.",
              idempotencyKey: `harness-screen-evidence:${runId || "unknown"}`,
              maxAttempts: 1,
            },
          };
        }
        if (screenState?.result?.ok === false && (screenState.failureRetries ?? 0) < 1) {
          screenState.failureRetries = (screenState.failureRetries ?? 0) + 1;
          screenState.called = false;
          screenState.toolCallId = undefined;
          screenState.result = undefined;
          return {
            action: "revise",
            reason: "GUI verification failed; one bounded retry is required.",
            retry: {
              instruction:
                "Retry harness_screen_inspect exactly once. If it fails again, report the returned safe error and no unverified fact.",
              idempotencyKey: `harness-screen-failure-retry:${runId || "unknown"}`,
              maxAttempts: 1,
            },
          };
        }
        if (sessionKey && screenState?.result) {
          const isCoupang = /(?:쿠팡|coupang)/i.test(screenState.question);
          const pendingScreenEvidence = {
            expiresAt: Date.now() + 5 * 60_000,
            text: isCoupang ? deterministicCoupangEvidenceReply(screenState.result) : undefined,
            mediaPaths: disposablePeekabooCapturePaths(screenState.result),
            evidenceKeys,
            sessionKey,
          };
          pendingScreenEvidence.mediaIdentities = Object.fromEntries(
            pendingScreenEvidence.mediaPaths.flatMap((imagePath) => {
              try {
                const stat = fs.statSync(imagePath);
                return [[imagePath, { dev: stat.dev, ino: stat.ino }]];
              } catch {
                return [];
              }
            }),
          );
          for (const key of evidenceKeys) {
            pendingCoupangEvidenceReplies.set(key, pendingScreenEvidence);
          }
          enqueuePendingState(
            pendingCoupangEvidenceSessions,
            sessionKey,
            pendingScreenEvidence,
          );
          schedulePendingCaptureCleanup(pendingScreenEvidence);
        }
        if (verificationState && sessionKey) {
          const successfulTools = verificationState.toolResults
            .filter((result) => result.success)
            .map((result) => result.toolName);
          if (successfulTools.length === 0 && verificationState.finalizeAttempts < 1) {
            verificationState.finalizeAttempts += 1;
            return {
              action: "revise",
              reason: "CEO verification answers require direct evidence.",
              retry: {
                instruction:
                  "Use the applicable read-only tool and provide its direct evidence. Prefer a screen capture for GUI state. If no evidence can be obtained, explicitly report verification failure.",
                idempotencyKey: `harness-ceo-verification:${runId}`,
                maxAttempts: 1,
              },
            };
          }
          const pendingVerification = {
            expiresAt: Date.now() + 5 * 60_000,
            successfulTools: [...new Set(successfulTools)],
            failed: successfulTools.length === 0,
            evidenceKeys,
            sessionKey,
          };
          for (const key of evidenceKeys) {
            pendingVerificationReplies.set(key, pendingVerification);
          }
          enqueuePendingState(
            pendingVerificationSessions,
            sessionKey,
            pendingVerification,
          );
          schedulePendingVerificationCleanup(pendingVerification);
        }
        return { action: "continue" };
      },
      { priority: 1000 },
    );
    api.on(
      "reply_payload_sending",
      async (event, context) => {
        pruneRuns();
        const pending = pendingStateFor(
          pendingCoupangEvidenceReplies,
          pendingCoupangEvidenceSessions,
          event,
          context,
        );
        const verification = pendingStateFor(
          pendingVerificationReplies,
          pendingVerificationSessions,
          event,
          context,
        );
        if (!pending && !verification) return;
        const existingMedia = [
          ...(Array.isArray(event.payload?.mediaUrls) ? event.payload.mediaUrls : []),
          event.payload?.mediaUrl,
        ].filter(Boolean);
        const mediaUrls = [...new Set([...existingMedia, ...(pending?.mediaPaths ?? [])])];
        const baseText = pending?.text ?? event.payload?.text ?? "";
        const evidenceText =
          mediaUrls.length > 0
            ? "증빙: 첨부한 실제 화면 캡처"
            : verification?.failed
              ? "증빙 확보 실패: 직접 확인 가능한 도구 결과가 없어 완료로 처리하지 않았습니다."
              : verification?.successfulTools?.length
                ? `증빙: ${verification.successfulTools.join(", ")} 실제 실행 결과`
                : "";
        const text = composeEvidenceReplyText({
          baseText,
          pendingText: pending?.text,
          evidenceText,
          verificationFailed: verification?.failed,
        });
        const dispatchKey = dispatchedEvidenceKey(
          { ...event, payload: { ...event.payload, text } },
          context,
        );
        if (dispatchKey && pending) {
          enqueuePendingState(dispatchedCoupangEvidenceSessions, dispatchKey, pending);
        }
        if (dispatchKey && verification) {
          enqueuePendingState(dispatchedVerificationSessions, dispatchKey, verification);
        }
        return {
          payload: {
            ...event.payload,
            text,
            ...(mediaUrls.length > 0 ? { mediaUrls, sensitiveMedia: true } : {}),
          },
        };
      },
      { priority: 1000 },
    );
    api.on("message_sent", async (event, context) => {
      const dispatchKey = dispatchedEvidenceKey(event, context);
      const pending = dispatchedCoupangEvidenceSessions.get(dispatchKey)?.[0];
      if (pending?.cleanupTimer) clearTimeout(pending.cleanupTimer);
      const pendingVerification = dispatchedVerificationSessions.get(dispatchKey)?.[0];
      if (pendingVerification?.cleanupTimer) clearTimeout(pendingVerification.cleanupTimer);
      for (const imagePath of pending?.mediaPaths ?? []) {
        try {
          const moved = moveDisposableCaptureToTrash(
            imagePath,
            pending.mediaIdentities?.[imagePath],
          );
          if (!moved) api.logger?.warn?.("peekaboo capture delivery cleanup was not applied");
        } catch (error) {
          api.logger?.warn?.(`peekaboo capture trash cleanup failed: ${error.message}`);
        }
      }
      deletePendingState(
        pendingCoupangEvidenceReplies,
        pendingCoupangEvidenceSessions,
        pending,
      );
      deletePendingState(
        pendingVerificationReplies,
        pendingVerificationSessions,
        pendingVerification,
      );
      deleteStateFromAllQueues(dispatchedCoupangEvidenceSessions, pending);
      deleteStateFromAllQueues(dispatchedVerificationSessions, pendingVerification);
    });
    api.on("agent_end", async (event, context) => {
      clearSajuRun(event, context);
      clearKnowledgeRun(event, context);
      clearCopilotUsageRun(event, context);
      clearBrowserOpenRun(event, context);
      clearScreenInspectRun(event, context);
      clearCoupangDetailOpenRun(event, context);
      clearPumpRun(event, context);
      clearVerificationRun(event, context);
    });
  },
};
