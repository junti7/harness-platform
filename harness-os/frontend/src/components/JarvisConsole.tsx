import { memo, useState } from 'react'
import type { FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { JarvisResponse } from './types'
import { renderTableCell, textFromNode } from './SparkChart'
import { formatDueDateWithCountdown } from './utils'

const BOX_TABLE_RE = /[┌┬┐├┼┤└┴┘│]/
const PIPE_TABLE_LINE_RE = /^\s*\|.*\|\s*$/m

function isPreformattedTableOutput(text: string): boolean {
  if (BOX_TABLE_RE.test(text)) return true
  const lines = text.split('\n')
  const pipeLines = lines.filter(line => PIPE_TABLE_LINE_RE.test(line)).length
  return pipeLines >= 3
}

type ParsedTable = { leadLines: string[]; headers: string[]; rows: string[][] }

function isDecorationLine(line: string): boolean {
  return line.replace(/[|┌┬┐├┼┤└┴┘─\-\s]/g, '').length === 0
}

function parseAsciiTable(text: string): ParsedTable | null {
  const lines = text.split('\n')
  const parsedRows: string[][] = []
  let firstRowLineIndex = -1
  for (let i = 0; i < lines.length; i++) {
    const normalized = lines[i].replaceAll('│', '|')
    if (!normalized.includes('|')) continue
    if (isDecorationLine(normalized)) continue
    const rawCells = normalized.split('|').map(c => c.trim())
    const cells = rawCells.length >= 2 && rawCells[0] === '' && rawCells[rawCells.length - 1] === ''
      ? rawCells.slice(1, -1) : rawCells
    const nonEmptyCount = cells.filter(c => c.length > 0).length
    if (nonEmptyCount < 2) continue
    if (firstRowLineIndex < 0) firstRowLineIndex = i
    parsedRows.push(cells)
  }
  if (parsedRows.length < 2) return null
  const columnCount = Math.max(...parsedRows.map(r => r.length))
  const normalizedRows = parsedRows.map(row =>
    row.length === columnCount ? row : [...row, ...Array.from({ length: columnCount - row.length }, () => '')]
  )
  const leadLines = firstRowLineIndex <= 0 ? []
    : lines.slice(0, firstRowLineIndex).map(l => l.trim()).filter(l => l.length > 0 && !isDecorationLine(l))
  return { leadLines, headers: normalizedRows[0], rows: normalizedRows.slice(1) }
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
            <p translate="no">Jarvis가 작업 중입니다…</p>
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
        const parsedTable = parseAsciiTable(entry.output)
        const dueColumnIndexes = parsedTable
          ? parsedTable.headers
              .map((h, idx) => ({ h: h.toLowerCase(), idx }))
              .filter(({ h }) => ['기한', 'due', 'due date', 'deadline'].some(k => h.includes(k)))
              .map(({ idx }) => idx)
          : []
        return (
          <article key={`${entry.generated_at}-${entry.command}`} className="jarvis-entry">
            <p className="jarvis-cmd">→ {entry.command}</p>
            <div className="jarvis-rendered">
              {parsedTable ? (
                <div className="jarvis-table-shell">
                  {parsedTable.leadLines.map(line => <p key={line} className="jarvis-table-lead">{line}</p>)}
                  <div className="jarvis-table-wrap">
                    <table className="jarvis-table">
                      <thead><tr>{parsedTable.headers.map((h, i) => <th key={`${h}-${i}`}>{h}</th>)}</tr></thead>
                      <tbody>
                        {parsedTable.rows.map((row, ri) => (
                          <tr key={`row-${ri}`}>
                            {row.map((cell, ci) => (
                              <td key={`cell-${ri}-${ci}`}>
                                {dueColumnIndexes.includes(ci) ? formatDueDateWithCountdown(cell) : renderTableCell(cell)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : isPreformattedTableOutput(entry.output) ? (
                <pre className="jarvis-preformatted">{entry.output}</pre>
              ) : (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ children }) => <h4>{children}</h4>,
                    h2: ({ children }) => <h5>{children}</h5>,
                    h3: ({ children }) => <h6>{children}</h6>,
                    p: ({ children }) => <p>{children}</p>,
                    li: ({ children }) => <li>{children}</li>,
                    code: ({ children }) => <code>{children}</code>,
                    blockquote: ({ children }) => <blockquote>{children}</blockquote>,
                    table: ({ children }) => (
                      <div className="jarvis-table-shell">
                        <div className="jarvis-table-wrap">
                          <table className="jarvis-table">{children}</table>
                        </div>
                      </div>
                    ),
                    th: ({ children }) => <th>{children}</th>,
                    td: ({ children }) => {
                      const text = textFromNode(children)
                      if (text === null) return <td>{children}</td>
                      return <td>{renderTableCell(text)}</td>
                    },
                  }}
                >
                  {entry.output}
                </ReactMarkdown>
              )}
            </div>
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
    '실행 전 체크해야 할 게이트를 pre-trade checklist로 요약해줘',
  ]
  const templates = viewRole === 'ceo' ? templateCommands : vpTemplates.map(t => ({ label: 'Analyst', command: t }))

  return (
    <section className="panel jarvis-panel">
      <div className="panel-head">
        <h3>Jarvis — Trading Desk Console</h3>
        <p className="panel-desc">operator console · 명령 실행 · 결과 로그</p>
      </div>
      {error && <div className="section-error" role="alert">Jarvis: {error}</div>}
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
        <input
          id="jarvis-input"
          value={command}
          onChange={e => setCommand(e.target.value)}
          placeholder="예: 오늘 장 시작 전 포지션 계획을 리스크 기준으로 정리해줘"
          disabled={invoking}
          autoComplete="off"
        />
        <button type="submit" disabled={invoking} translate="no">
          {invoking ? 'WORKING…' : 'RUN'}
        </button>
      </form>
      <JarvisLogFeed invoking={invoking} logs={logs} />
    </section>
  )
}
