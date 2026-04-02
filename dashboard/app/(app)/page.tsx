'use client'

import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useTasks } from '@/hooks/useTasks'
import { useApprovals } from '@/hooks/useApprovals'
import { Badge } from '@/components/ui/Badge'
import { STATUS_BADGES } from '@/lib/constants'
import {
  LayoutDashboard,
  CheckCircle,
  Clock,
  AlertTriangle,
  ShieldCheck,
} from 'lucide-react'

export default function OverviewPage() {
  const { orgId, currentOrg } = useCurrentOrg()
  const { data: tasksData } = useTasks(orgId)
  const { data: approvals } = useApprovals(orgId)

  const tasks = tasksData?.items || []
  const pendingApprovals = approvals?.filter((a) => a.status === 'pending') || []

  const stats = {
    total: tasks.length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    running: tasks.filter((t) => t.status === 'running').length,
    failed: tasks.filter((t) => t.status === 'failed').length,
    awaiting: tasks.filter((t) => t.status === 'awaiting_approval').length,
  }

  const successRate =
    stats.total > 0
      ? Math.round((stats.completed / stats.total) * 100)
      : 0

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Overview
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {currentOrg?.name || 'Selecciona una organización'}
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <StatCard
          icon={<LayoutDashboard className="h-5 w-5 text-blue-600" />}
          label="Total tareas"
          value={stats.total}
        />
        <StatCard
          icon={<CheckCircle className="h-5 w-5 text-green-600" />}
          label="Completadas"
          value={stats.completed}
          subtext={`${successRate}% éxito`}
        />
        <StatCard
          icon={<Clock className="h-5 w-5 text-blue-600" />}
          label="Ejecutando"
          value={stats.running}
        />
        <StatCard
          icon={<AlertTriangle className="h-5 w-5 text-red-600" />}
          label="Errores"
          value={stats.failed}
        />
        <StatCard
          icon={<ShieldCheck className="h-5 w-5 text-amber-600" />}
          label="HITL pendientes"
          value={pendingApprovals.length}
          highlight={pendingApprovals.length > 0}
        />
      </div>

      {/* Recent tasks */}
      <div className="rounded-lg border bg-white dark:bg-gray-900 dark:border-gray-800">
        <div className="border-b px-6 py-4 dark:border-gray-800">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">Tareas recientes</h3>
        </div>
        <div className="divide-y dark:divide-gray-800">
          {tasks.slice(0, 10).map((task) => {
            const badge = STATUS_BADGES[task.status] || STATUS_BADGES['pending']
            return (
              <div
                key={task.task_id}
                className="flex items-center justify-between px-6 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{task.flow_type}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{task.task_id.slice(0, 12)}...</p>
                </div>
                <Badge className={badge.className}>{badge.label}</Badge>
              </div>
            )
          })}
          {tasks.length === 0 && (
            <p className="px-6 py-8 text-center text-sm text-gray-400">
              No hay tareas aún
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  subtext,
  highlight,
}: {
  icon: React.ReactNode
  label: string
  value: number
  subtext?: string
  highlight?: boolean
}) {
  return (
    <div
      className={`rounded-lg border bg-white p-4 dark:bg-gray-900 dark:border-gray-800 ${
        highlight ? 'border-amber-300 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-900/10' : ''
      }`}
    >
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
          {subtext && (
            <p className="text-xs text-gray-400 dark:text-gray-500">{subtext}</p>
          )}
        </div>
      </div>
    </div>
  )
}
