'use client'

import { createContext, useContext, useState, useRef, useEffect, type ReactNode } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'

interface BuilderTabContextValue {
  activeTab: string
  setActiveTab: (tab: string) => void
}

const BuilderTabContext = createContext<BuilderTabContextValue | null>(null)

export function useBuilderTab(): BuilderTabContextValue {
  const ctx = useContext(BuilderTabContext)
  if (!ctx) {
    throw new Error('useBuilderTab must be used within a BuilderTabProvider')
  }
  return ctx
}

interface BuilderTabProviderProps {
  children: ReactNode
  defaultTab?: string
}

const VALID_TABS = ['agent-form', 'crew-canvas']

export function BuilderTabProvider({
  children,
  defaultTab = 'agent-form',
}: BuilderTabProviderProps) {
  const searchParams = useSearchParams()
  const router = useRouter()
  const initialized = useRef(false)

  const tabParam = searchParams.get('tab')
  const initialTab = tabParam && VALID_TABS.includes(tabParam) ? tabParam : defaultTab

  const [activeTab, setActiveTabState] = useState(initialTab)

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true
    const tab = searchParams.get('tab')
    if (tab && VALID_TABS.includes(tab) && tab !== activeTab) {
      setActiveTabState(tab)
    }
  }, [searchParams, activeTab])

  function setActiveTab(tab: string) {
    setActiveTabState(tab)
    router.replace(`?tab=${tab}`, { scroll: false })
  }

  return (
    <BuilderTabContext.Provider value={{ activeTab, setActiveTab }}>
      {children}
    </BuilderTabContext.Provider>
  )
}
