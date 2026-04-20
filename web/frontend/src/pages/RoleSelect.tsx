import { useNavigate } from 'react-router-dom'
import type { Role } from '../types'

const ROLES: { key: Role; icon: string; label: string; zhLabel: string; desc: string; featured?: boolean }[] = [
  {
    key: 'consumer',
    icon: 'shopping_bag',
    label: 'Consumer',
    zhLabel: '消费者',
    desc: '查看价格透明度报告，对不公平定价提出投诉，获取维权建议与历史市场数据参考。',
  },
  {
    key: 'regulator',
    icon: 'gavel',
    label: 'Regulator',
    zhLabel: '政府监管',
    desc: '利用 AI 驱动的市场分析，开展执法认定、法条适用判断、证据链审查，管理案卷并追踪法规溯源。',
    featured: true,
  },
  {
    key: 'merchant',
    icon: 'storefront',
    label: 'Merchant',
    zhLabel: '网店商家',
    desc: '审计定价策略是否合规，获取整改建议，建立价格合规预防机制，维护良好经营信誉。',
  },
]

export default function RoleSelect() {
  const navigate = useNavigate()

  const go = (role: Role) => navigate(`/chat?role=${role}`)

  return (
    <div className="bg-surface text-on-surface font-body min-h-screen flex flex-col relative overflow-hidden bg-watermark">
      {/* Header */}
      <header className="w-full bg-surface-container-lowest px-8 py-6 shadow-ambient flex justify-center items-center z-50">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined icon-fill text-primary text-3xl">account_balance</span>
          <h1 className="font-headline font-black text-2xl text-primary tracking-tight m-0">Jurisconsult AI</h1>
        </div>
      </header>

      {/* Main */}
      <main className="flex-grow flex flex-col items-center justify-center px-6 py-24 sm:px-12 z-10">
        <div className="text-center max-w-3xl mb-16 space-y-6">
          <h2 className="font-headline font-bold text-4xl sm:text-5xl text-primary leading-tight m-0">
            选择您的角色视角
          </h2>
          <p className="font-body text-lg text-on-surface-variant max-w-2xl mx-auto leading-relaxed m-0">
            欢迎使用价格合规智能分析平台。请选择您的身份，获取定制化的合规分析工具与法规溯源能力。
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl w-full">
          {ROLES.map((r) => (
            <div
              key={r.key}
              className={`bg-surface-container-lowest rounded-lg overflow-hidden flex flex-col hover:-translate-y-2 transition-transform duration-500 ease-[cubic-bezier(0.4,0,0.2,1)] group relative cursor-pointer ${
                r.featured
                  ? 'shadow-[0_20px_50px_rgba(27,54,93,0.12)] -mt-4 md:-mt-8 z-10 border-t-4 border-primary'
                  : 'shadow-ambient'
              }`}
              onClick={() => go(r.key)}
            >
              {!r.featured && <div className="h-2 w-full bg-surface-container-high" />}
              <div className="p-8 flex-grow flex flex-col items-center text-center space-y-6 relative">
                <div className={`rounded-full flex items-center justify-center mb-2 ${
                  r.featured
                    ? 'w-24 h-24 bg-primary-container shadow-inner'
                    : 'w-20 h-20 bg-surface-container-low group-hover:bg-primary-fixed transition-colors duration-500'
                }`}>
                  <span className={`material-symbols-outlined text-primary ${r.featured ? 'icon-fill text-5xl text-white' : 'text-4xl'}`}>
                    {r.icon}
                  </span>
                </div>
                <div className="space-y-3">
                  <h3 className="font-headline font-bold text-2xl text-primary m-0">{r.label}</h3>
                  <div className={`inline-flex items-center justify-center px-3 py-1 rounded-sm text-xs font-semibold uppercase tracking-wider ${
                    r.featured
                      ? 'bg-primary-fixed-dim font-bold text-primary'
                      : 'bg-surface-container-high text-on-surface-variant'
                  }`}>
                    {r.zhLabel}
                  </div>
                </div>
                <p className="font-body text-sm text-on-surface-variant leading-relaxed flex-grow m-0">{r.desc}</p>
                <button className={`w-full mt-6 px-6 rounded-xl font-semibold text-sm transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 cursor-pointer ${
                  r.featured
                    ? 'py-4 btn-gradient text-white shadow-md hover:shadow-lg'
                    : 'py-3 bg-surface-container-highest text-primary hover:btn-gradient hover:text-white'
                }`}>
                  进入工作台
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-24 text-center max-w-xl">
          <div className="flex items-center justify-center gap-2 text-outline mb-2">
            <span className="material-symbols-outlined text-sm">verified_user</span>
            <span className="font-body text-xs font-medium uppercase tracking-widest">本地安全运行</span>
          </div>
          <p className="font-body text-xs text-outline leading-relaxed m-0">
            本系统仅在本地运行，数据不上传至任何外部服务器。分析结果仅供参考，不构成法律意见。
          </p>
        </div>
      </main>
    </div>
  )
}
