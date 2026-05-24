import { platformLabel } from './utils'

const PLATFORM_ORDER = ['all', 'substack', 'maily'] as const

type Props = {
  selected: string
  available: string[]
  onSelect: (p: string) => void
  description: string
}

export function PlatformSelector({ selected, available, onSelect, description }: Props) {
  const availableSet = new Set(available)
  return (
    <section className="platform-bar" aria-label="Platform selector">
      <span className="platform-bar-label">Platform</span>
      <div className="platform-tabs" role="tablist">
        {PLATFORM_ORDER.map(platform => {
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
              {platform === 'maily' && isDisabled && (
                <span className="platform-soon">준비중</span>
              )}
            </button>
          )
        })}
      </div>
      <span className="platform-hint">{description}</span>
    </section>
  )
}
