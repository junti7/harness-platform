import { platformLabel } from './utils'

// Substack, Maily 사업 보류 결정에 따라 플랫폼 탭을 숨김
// 현재는 'all' 통합 뷰만 사용
const ALLOWED_PLATFORMS = new Set(['all'])

type Props = {
  selected: string
  available: string[]
  onSelect: (p: string) => void
  description: string
}

export function PlatformSelector({ selected, available, onSelect, description }: Props) {
  // Substack/Maily 등 보류중 플랫폼을 필터링
  const filteredAvailable = available.filter(p => ALLOWED_PLATFORMS.has(p))
  const availableSet = new Set(filteredAvailable)

  // 플랫폼이 'all' 하나밖엀 없으면 선택 바 자체 숨김
  if (filteredAvailable.length <= 1) return null

  return (
    <section className="platform-bar" aria-label="Platform selector">
      <span className="platform-bar-label">플랫폼</span>
      <div className="platform-tabs" role="tablist">
        {filteredAvailable.map(platform => {
          const isDisabled = !availableSet.has(platform)
          const isActive = selected === platform
          return (
            <button
              key={platform}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={['platform-tab', isActive ? 'active' : '', isDisabled ? 'disabled' : ''].filter(Boolean).join(' ')}
              onClick={() => { if (!isDisabled) onSelect(platform) }}
              disabled={isDisabled}
            >
              {platformLabel(platform)}
            </button>
          )
        })}
      </div>
      <span className="platform-hint">{description}</span>
    </section>
  )
}
