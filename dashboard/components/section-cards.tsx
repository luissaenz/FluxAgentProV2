'use client'

import { useTasks } from '@/hooks/useTasks'
import { useApprovals } from '@/hooks/useApprovals'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LayoutDashboard, CheckCircle, Clock, AlertTriangle, ShieldCheck } from 'lucide-react'

export function SectionCards() {
  const { orgId } = useCurrentOrg()
  const { data: tasksData } = useTasks(orgId)
  const { data: approvals } = useApprovals(orgId)

  const tasks = tasksData?.items || []
  const pendingApprovals = approvals?.filter((a) => a.status === 'pending').length || 0

  const stats = {
    total: tasks.length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    running: tasks.filter((t) => t.status === 'running').length,
    failed: tasks.filter((t) => t.status === 'failed').length,
  }

  const successRate =
    stats.total > 0
      ? Math.round((stats.completed / stats.total) * 100)
      : 0

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total tareas</CardTitle>
          <LayoutDashboard className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.total}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Completadas</CardTitle>
          <CheckCircle className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.completed}</div>
          <p className="text-xs text-muted-foreground">{successRate}% éxito</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Ejecutando</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.running}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Errores</CardTitle>
          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.failed}</div>
        </CardContent>
      </Card>

      <Card className={pendingApprovals > 0 ? 'border-amber-300 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-900/10' : ''}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">HITL pendientes</CardTitle>
          <ShieldCheck className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{pendingApprovals}</div>
        </CardContent>
      </Card>
    </div>
  )
}
