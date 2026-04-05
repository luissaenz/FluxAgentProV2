'use client'

import { ChevronsUpDown, LogOut, Building2 } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'

export function NavUser() {
  const { signOut, user } = useAuth()
  const { orgs, currentOrg, switchOrg } = useCurrentOrg()

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Building2 className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">{currentOrg?.name || 'Sin organización'}</span>
                <span className="truncate text-xs text-muted-foreground">{user?.email}</span>
              </div>
              <ChevronsUpDown className="ml-auto size-4" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>

          <DropdownMenuContent
            className="w-[--radix-dropdown-menu-trigger-width] min-w-56"
            side="right"
            align="end"
          >
            {orgs.length > 1 && (
              <>
                {orgs.map((org) => (
                  <DropdownMenuItem
                    key={org.id}
                    onClick={() => switchOrg(org)}
                    className={currentOrg?.id === org.id ? 'bg-accent' : ''}
                  >
                    <Building2 className="mr-2 h-4 w-4" />
                    {org.name}
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
              </>
            )}
            <DropdownMenuItem onClick={() => signOut()}>
              <LogOut className="mr-2 h-4 w-4" />
              Cerrar sesión
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
