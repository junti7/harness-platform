import { memo, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import Markdown from 'react-markdown'
import type { Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { JarvisResponse } from './types'
import { formatDueDateWithCountdown } from './utils'

const BOX_TABLE_RE = /[┌┬┐├┼┤└┴┘│]/
const PIPE_TABLE_LINE_RE = /^\s*\|.*\|\s*$/m
const MENTION_TOKEN_RE = /(^|\s)(@[a-z0-9_-]+)/gi
const ICON_SYMBOL_RE = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu
const LEADING_MENTION_RE = /^\s*(@[a-z0-9_-]+)/i

const JARVIS_MD_COMPONENTS: Components = {
  h1: ({ children, ...rest }) => <h4 className="jarvis-md-h1" {...rest}>{children}</h4>,
  h2: ({ children, ...rest }) => <h5 className="jarvis-md-h2" {...rest}>{children}</h5>,
  h3: ({ children, ...rest }) => <h6 className="jarvis-md-h3" {...rest}>{children}</h6>,
  h4: ({ children, ...rest }) => <p className="jarvis-md-h4" {...rest}>{children}</p>,
  p: ({ children, ...rest }) => <p className="jarvis-md-p" {...rest}>{children}</p>,
  ul: ({ children, ...rest }) => <ul className="jarvis-md-list" {...rest}>{children}</ul>,
  ol: ({ children, ...rest }) => <ol className="jarvis-md-list jarvis-md-ol" {...rest}>{children}</ol>,
  li: ({ children, ...rest }) => <li className="jarvis-md-li" {...rest}>{children}</li>,
  strong: ({ children, ...rest }) => <strong className="jarvis-md-strong" {...rest}>{children}</strong>,
  em: ({ children, ...rest }) => <em className="jarvis-md-em" {...rest}>{children}</em>,
  code: ({ children, className, ...rest }) => {
    const isBlock = className?.includes('language-')
    return isBlock
      ? <code className={`jarvis-md-codeblock ${className ?? ''}`} {...rest}>{children}</code>
      : <code className="jarvis-md-inline-code" {...rest}>{children}</code>
  },
  pre: ({ children, ...rest }) => <pre className="jarvis-md-pre" {...rest}>{children}</pre>,
  blockquote: ({ children, ...rest }) => <blockquote className="jarvis-md-blockquote" {...rest}>{children}</blockquote>,
  hr: () => <hr className="jarvis-md-hr" />,
  a: ({ children, href, ...rest }) => <a className="jarvis-md-link" href={href} target="_blank" rel="noopener noreferrer" {...rest}>{children}</a>,
  table: ({ children, ...rest }) => (
    <div className="jarvis-table-shell">
      <div className="jarvis-table-wrap">
        <table className="jarvis-table" {...rest}>{children}</table>
      </div>
    </div>
  ),
  th: ({ children, ...rest }) => <th className="jarvis-md-th" {...rest}>{children}</th>,
  td: ({ children, ...rest }) => <td className="jarvis-md-td" {...rest}>{children}</td>,
}

function isPreformattedTableOutput(text: string): boolean {
  if (BOX_TABLE_RE.test(text)) return true
  const lines = text.split('\n')
  const pipeLines = lines.filter(line => PIPE_TABLE_LINE_RE.test(line)).length
  return pipeLines >= 3
}

type ParsedBlock =
  | { type: 'markdown'; text: string }
  | { type: 'table'; headers: string[]; rows: string[][]; dueColumnIndexes: number[] }

function isDecorationLine(line: string): boolean {
  return line.replace(/[|┌┬┐├┼┤└┴┘─\-\s]/g, '').length === 0
}

function parseBlocks(text: string): ParsedBlock[] {
  const lines = text.split('\n')
  const blocks: ParsedBlock[] = []
  let currentMdLines: string[] = []

  let inTable = false
  let tableRows: string[][] = []

  const flushMd = () => {
    if (currentMdLines.length > 0) {
      blocks.push({ type: 'markdown', text: currentMdLines.join('\n') })
      currentMdLines = []
    }
  }

  const flushTable = () => {
    if (tableRows.length >= 2) {
       const columnCount = Math.max(...tableRows.map(r => r.length))
       const normRows = tableRows.map(row =>
         row.length === columnCount ? row : [...row, ...Array.from({ length: columnCount - row.length }, () => '')]
       )
       const headers = normRows[0]
       const dueColumnIndexes = headers.map((h, idx) => ({ h: h.toLowerCase(), idx }))
         .filter(({ h }) => ['기한', 'due', 'due date', 'deadline'].some(k => h.includes(k)))
         .map(({ idx }) => idx)
       blocks.push({ type: 'table', headers, rows: normRows.slice(1), dueColumnIndexes })
    } else if (tableRows.length > 0) {
       currentMdLines.push(...tableRows.map(r => r.join(' | ')))
    }
    tableRows = []
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const normalized = line.replaceAll('│', '|')
    const isTableRow = normalized.includes('|') && !isDecorationLine(normalized)

    if (isTableRow) {
      if (!inTable) {
        flushMd()
        inTable = true
      }
      const rawCells = normalized.split('|').map(c => c.trim())
      const cells = rawCells.length >= 2 && rawCells[0] === '' && rawCells[rawCells.length - 1] === ''
        ? rawCells.slice(1, -1) : rawCells
      if (cells.filter(c => c.length > 0).length >= 2) {
         tableRows.push(cells)
      } else {
         if (inTable) flushTable()
         inTable = false
         currentMdLines.push(line)
      }
    } else {
      if (inTable) {
        if (!isDecorationLine(normalized)) {
          flushTable()
          inTable = false
          currentMdLines.push(line)
        }
      } else {
        currentMdLines.push(line)
      }
    }
  }

  if (inTable) flushTable()
  flushMd()

  return blocks
}
function escapeHtml(text: string): string {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function renderMentionHighlightedHtml(text: string): string {
  const escaped = escapeHtml(text)
  return escaped.replace(MENTION_TOKEN_RE, (_, prefix, mention) => `${prefix}<mark class="jarvis-mention-token">${mention}</mark>`)
}

function normalizeOutputForRender(raw: string): string {
  let text = raw ?? ''
  const escapedNewlineCount = (text.match(/\\n/g) || []).length
  const realNewlineCount = (text.match(/\n/g) || []).length
  if (escapedNewlineCount > 0 && escapedNewlineCount >= realNewlineCount) {
    text = text.replace(/\\r\\n/g, '\n').replace(/\\n/g, '\n').replace(/\\t/g, '  ')
  }
  text = text
    .replace(ICON_SYMBOL_RE, '')
    .replace(/^(#{1,6})([^\s#])/gm, '$1 $2')
    .replace(/\r\n/g, '\n')
  return text
}

function detectLeadingMention(text: string): string | null {
  const match = text.match(LEADING_MENTION_RE)
  return match ? match[1] : null
}

const INFLIGHT_STEPS = ['요청을 안전하게 검사하는 중', '관련 컨텍스트를 수집하는 중', '에이전트 응답을 생성하는 중', '결과를 포맷팅하는 중']

type LogFeedProps = { invoking: boolean; logs: JarvisResponse[] }

const JarvisLogFeed = memo(function JarvisLogFeed({ invoking, logs }: LogFeedProps) {
  return (
    <div className="jarvis-log">
      {invoking && (
        <article className="jarvis-entry in-flight">
          <div className="inflight-head">
            <span className="spinner" />
            <p translate="no">운영 도우미가 작업 중입니다…</p>
          </div>
          <ol className="inflight-steps">
            {INFLIGHT_STEPS.map((step, i) => <li key={step} className={i === 0 ? 'active' : ''}>{step}</li>)}
          </ol>
        </article>
      )}
      {logs.length === 0 && !invoking && (
        <p className="jarvis-placeholder">명령 기록이 없습니다. 첫 명령을 실행하세요.</p>
      )}
      {logs.map(entry => {
        const normalizedOutput = normalizeOutputForRender(entry.output)
        const isPreform = isPreformattedTableOutput(normalizedOutput) && !normalizedOutput.includes('|')
        const blocks = isPreform ? [] : parseBlocks(normalizedOutput)

        return (
          <article key={`${entry.generated_at}-${entry.command}`} className="jarvis-entry">
            <p className="jarvis-cmd">→ {entry.command}</p>
            <div className="jarvis-rendered">
              {isPreform ? (
                <pre className="jarvis-preformatted">{normalizedOutput}</pre>
              ) : (
                blocks.map((block, idx) => {
                  if (block.type === 'markdown') {
                    return (
                      <Markdown
                        key={`block-${idx}`}
                        remarkPlugins={[remarkGfm]}
                        components={JARVIS_MD_COMPONENTS}
                      >
                        {block.text}
                      </Markdown>
                    )
                  }
                  return (
                    <div key={`block-${idx}`} className="jarvis-table-shell">
                      <div className="jarvis-table-wrap">
                        <table className="jarvis-table">
                          <thead><tr>{block.headers.map((h, i) => <th key={`${h}-${i}`}>{h}</th>)}</tr></thead>
                          <tbody>
                            {block.rows.map((row, ri) => (
                              <tr key={`row-${ri}`}>
                                {row.map((cell, ci) => (
                                  <td key={`cell-${ri}-${ci}`}>
                                    {block.dueColumnIndexes.includes(ci)
                                      ? formatDueDateWithCountdown(cell)
                                      : <Markdown remarkPlugins={[remarkGfm]} components={JARVIS_MD_COMPONENTS}>{cell}</Markdown>}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
            {!!entry.relay_notes?.length && (
              <div className="jarvis-relay-notes">
                <span className="jarvis-relay-label">Slack</span>
                {entry.relay_notes.map(note => {
                  const isOk = note.includes('완료')
                  const isFail = note.includes('실패') || note.includes('미설정') || note.includes('건너뜀')
                  return (
                    <span
                      key={note}
                      className={`jarvis-relay-chip ${isOk ? 'ok' : isFail ? 'fail' : 'info'}`}
                    >
                      {isOk ? '✓' : isFail ? '✕' : '·'} {note}
                    </span>
                  )
                })}
              </div>
            )}
            <small className="jarvis-timestamp">{entry.generated_at}</small>
          </article>
        )
      })}
    </div>
  )
})

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
  templateCommands?: Array<{ label: string; command: string }>
  viewRole: 'ceo' | 'vp'
}

export function JarvisConsole({ apiBase, authHeaders, templateCommands = [], viewRole }: Props) {
  const [command, setCommand] = useState('')
  const [invoking, setInvoking] = useState(false)
  const [logs, setLogs] = useState<JarvisResponse[]>([])
  const [error, setError] = useState<string | null>(null)
  const [coarsePointer, setCoarsePointer] = useState(false)

  useEffect(() => {
    const media = window.matchMedia('(pointer: coarse)')
    const update = () => setCoarsePointer(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const trimmed = command.trim()
    if (!trimmed) return
    setInvoking(true)
    setError(null)
    try {
      const response = await fetch(`${apiBase}/api/jarvis/invoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ command: trimmed }),
      })
      if (!response.ok) throw new Error(`Jarvis API ${response.status}`)
      const payload = (await response.json()) as JarvisResponse
      setLogs(prev => [payload, ...prev].slice(0, 12))
      setCommand('')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      setLogs(prev => [
        { command: trimmed, output: `오류: ${message}`, generated_at: new Date().toISOString() },
        ...prev,
      ])
    } finally {
      setInvoking(false)
    }
  }

  const vpTemplates = [
    '오늘 관찰해야 할 리스크 트리거 5개만 우선순위로 정리해줘',
    '리스크-리워드 비가 좋은 시나리오 3개를 근거와 함께 제시해줘',
    '실행 전 확인해야 할 승인·안전 조건을 쉬운 체크리스트로 요약해줘',
  ]
  const templates = viewRole === 'ceo' ? templateCommands : vpTemplates.map(t => ({ label: '애널리스트', command: t }))
  const leadingMention = detectLeadingMention(command)

  return (
    <section className="panel jarvis-panel">
      <div className="panel-head">
        <h3>운영 도우미</h3>
        <p className="panel-desc">팀별 자동화에게 질문하고 실행 결과를 확인합니다. 예: @Friday 오늘 핵심 지표 이상징후 3개와 대응 우선순위 정리</p>
      </div>
      {error && <div className="section-error" role="alert">운영 도우미: {error}</div>}
      {templates.length > 0 && (
        <div className="cmd-templates">
          {templates.map(tpl => (
            <button key={tpl.command} type="button" className="cmd-chip" onClick={() => setCommand(tpl.command)}>
              <span className="cmd-chip-label">{tpl.label}</span>
              <span className="cmd-chip-text">{tpl.command}</span>
            </button>
          ))}
        </div>
      )}
      <form onSubmit={handleSubmit} className="jarvis-form">
        {coarsePointer ? (
          <div className="jarvis-input-wrap mobile-safe">
            {!!leadingMention && (
              <p className="jarvis-mobile-mention-hint">
                대상 <mark className="jarvis-mention-token">{leadingMention.toLowerCase()}</mark>
              </p>
            )}
            <input
              id="jarvis-input"
              className="jarvis-input-mobile"
              value={command}
              onChange={e => setCommand(e.target.value)}
              placeholder="예: @friday 오늘 핵심 지표 이상징후 3개와 대응 우선순위 정리해줘"
              disabled={invoking}
              autoComplete="off"
              inputMode="text"
            />
          </div>
        ) : (
          <div className="jarvis-input-wrap">
            <div
              className="jarvis-input-highlight"
              aria-hidden
              dangerouslySetInnerHTML={{ __html: renderMentionHighlightedHtml(command) || '&nbsp;' }}
            />
            {!command && <span className="jarvis-input-placeholder">예: 오늘 장 시작 전 포지션 계획을 리스크 기준으로 정리해줘</span>}
            <input
              id="jarvis-input"
              className="jarvis-input-real"
              value={command}
              onChange={e => setCommand(e.target.value)}
              disabled={invoking}
              autoComplete="off"
            />
          </div>
        )}
        <button type="submit" disabled={invoking}>
          {invoking ? '실행중…' : '실행'}
        </button>
      </form>
      <JarvisLogFeed invoking={invoking} logs={logs} />
    </section>
  )
}
