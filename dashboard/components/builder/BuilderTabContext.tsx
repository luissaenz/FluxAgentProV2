'use client'

import { createContext, useContext, useState, type ReactNode } from 'react'

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

export function BuilderTabProvider({
  children,
  defaultTab = 'agent-form',
}: BuilderTabProviderProps) {
  const [activeTab, setActiveTab] = useState(defaultTab)

  return (
    <BuilderTabContext.Provider value={{ activeTab, setActiveTab }}>
      {children}
    </BuilderTabContext.Provider>
  )
}
