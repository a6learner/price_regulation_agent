import { NODE_NAMES, NODE_LABELS } from '../types'
import type { NodeState } from '../types'

interface Props {
  nodes: NodeState[]
}

export default function ProgressTimeline({ nodes }: Props) {
  const stateMap = Object.fromEntries(nodes.map(n => [n.name, n.status]))

  return (
    <div className="bg-surface-container-lowest p-5 rounded-lg ghost-border shadow-[0_12px_40px_rgba(27,54,93,0.02)]">
      <div className="relative flex justify-between items-center px-4">
        {/* Background line */}
        <div className="absolute left-4 right-4 top-1/2 -translate-y-1/2 h-[1px] bg-outline-variant/20 z-0" />

        {NODE_NAMES.map((name) => {
          const status = stateMap[name] || 'pending'
          return (
            <div key={name} className={`relative z-10 flex flex-col items-center gap-2 ${status === 'pending' ? 'opacity-40' : ''}`}>
              {status === 'done' ? (
                <div className="w-3 h-3 rounded-full bg-secondary shadow-[0_0_8px_rgba(0,109,54,0.3)] border-2 border-surface-container-lowest" />
              ) : status === 'active' ? (
                <div className="w-3 h-3 rounded-full bg-primary-container flex items-center justify-center border-2 border-surface-container-lowest shadow-[0_0_0_4px_rgba(27,54,93,0.1)]">
                  <div className="w-1 h-1 bg-white rounded-full" />
                </div>
              ) : (
                <div className="w-3 h-3 rounded-full bg-outline-variant border-2 border-surface-container-lowest" />
              )}
              <span className={`text-[10px] font-medium uppercase tracking-wider ${
                status === 'active' ? 'font-bold text-primary' : 'text-on-surface-variant'
              }`}>
                {NODE_LABELS[name]}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
