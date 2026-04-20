import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

/** 防止子组件渲染异常导致整页白屏 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[UI]', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-8 bg-surface text-on-surface font-body">
          <p className="text-lg font-headline text-primary">页面渲染出错</p>
          <p className="text-sm text-on-surface-variant max-w-md text-center">
            {this.state.error.message}
          </p>
          <button
            type="button"
            className="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm cursor-pointer"
            onClick={() => window.location.reload()}
          >
            刷新页面
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
