import { FloatingNav } from '@/components/floating-nav'
import { Separator } from '@/components/ui/separator'
import { ThemeToggle } from '@/components/theme-toggle'
import { NavUser } from '@/components/nav-user'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'

export function SiteHeader() {
  const { currentOrg } = useCurrentOrg()

  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4 backdrop-blur-md bg-background/80 sticky top-0 z-30">
      <FloatingNav />
      <Separator orientation="vertical" className="mr-2 h-4" />
      <div className="flex items-center gap-2 text-sm font-medium">
        <span className="hidden md:inline">FluxAgentPro</span>
        {currentOrg?.name && (
          <>
            <Separator orientation="vertical" className="h-4" />
            <span className="text-muted-foreground">{currentOrg.name}</span>
          </>
        )}
      </div>
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
        <div className="md:hidden">
          <NavUser />
        </div>
      </div>
    </header>
  )
}
