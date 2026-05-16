import type { ErrorInfo, ReactNode } from 'react'
import { Component } from 'react'

interface BuilderErrorBoundaryProps {
  children: ReactNode
}

interface BuilderErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class BuilderErrorBoundary extends Component<BuilderErrorBoundaryProps, BuilderErrorBoundaryState> {
  constructor(props: BuilderErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): BuilderErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('BuilderErrorBoundary caught:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full flex-col items-center justify-center space-y-4 rounded-lg border border-destructive/50 bg-destructive/10 p-8">
          <div className="text-center">
            <h2 className="mb-2 text-lg font-semibold text-destructive">
              Canvas Error
            </h2>
            <p className="mb-4 max-w-md text-sm text-muted-foreground">
              {this.state.error?.message || 'An unexpected error occurred in the Agent Builder canvas. The rest of the page remains available.'}
            </p>
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90"
            >
              Retry
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
