'use client'

import { useMetrics } from '@/hooks/useMetrics'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { LayoutDashboard, CheckCircle, Clock, AlertTriangle, ShieldCheck, Coins } from 'lucide-react'

export function SectionCards() {
  const { orgId } = useCurrentOrg()
  const { data: metrics, isLoading } = useMetrics(orgId)

  const stats = {
    total: metrics?.tasks.total ?? 0,
    completed: metrics?.tasks.by_status['completed'] ?? 0,
    running: metrics?.tasks.by_status['running'] ?? 0,
    failed: metrics?.tasks.by_status['failed'] ?? 0,
    tokens: metrics?.tokens.total ?? 0,
    pendingApprovals: metrics?.approvals.pending ?? 0,
  }

  const successRate =
    stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
      <MetricCard
        title="Total tareas"
        value={stats.total}
        icon={<LayoutDashboard className="h-4 w-4 text-muted-foreground" />}
        loading={isLoading}
      />
      <MetricCard
        title="Completadas"
        value={stats.completed}
        subtitle={`${successRate}% exito`}
        icon={<CheckCircle className="h-4 w-4 text-muted-foreground" />}
        loading={isLoading}
      />
      <MetricCard
        title="Ejecutando"
        value={stats.running}
        icon={<Clock className="h-4 w-4 text-muted-foreground" />}
        loading={isLoading}
      />
      <MetricCard
        title="Errores"
        value={stats.failed}
        icon={<AlertTriangle className="h-4 w-4 text-muted-foreground" />}
        loading={isLoading}
      />
      <MetricCard
        title="Tokens totales"
        value={stats.tokens}
        format="number"
        icon={<Coins className="h-4 w-4 text-muted-foreground" />}
        loading={isLoading}
      />
      <Card className={stats.pendingApprovals > 0 ? 'border-amber-300 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-900/10' : ''}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">HITL pendientes</CardTitle>
          <ShieldCheck className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-8 w-16" />
          ) : (
            <div className="text-2xl font-bold">{stats.pendingApprovals}</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function MetricCard({
  title,
  value,
  subtitle,
  icon,
  loading,
  format,
}: {
  title: string
  value: number
  subtitle?: string
  icon: React.ReactNode
  loading?: boolean
  format?: 'number'
}) {
  const displayValue = format === 'number' ? value.toLocaleString() : value.toString()

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <>
            <div className="text-2xl font-bold">{displayValue}</div>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
