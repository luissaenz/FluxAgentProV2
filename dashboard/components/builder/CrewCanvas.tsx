'use client'

import { useState, useCallback, useRef, useEffect, useMemo, type DragEvent } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Node,
  ReactFlowProvider,
  useReactFlow,
} from 'reactflow'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Download,
  Play,
  Code,
  Share2,
  Plus,
  Layers,
  Save,
} from 'lucide-react'

import { api } from '@/lib/api'
import { createClient } from '@/lib/supabase'
import { generateCrewPy } from '@/lib/crewCodeGen'
import { canvasToExportPayload, nodesToSnapshot, snapshotToNodes } from '@/lib/canvasUtils'
import { CREW_TEMPLATES } from '@/lib/crewTemplates'
import { AgentNode } from '@/components/builder/nodes/AgentNode'
import { TaskNode } from '@/components/builder/nodes/TaskNode'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'

import 'reactflow/dist/style.css'

const LOCALSTORAGE_KEY = 'fap_crew_canvas_snapshot'
const AUTOSAVE_INTERVAL = 30000

const nodeTypes = {
  agentNode: AgentNode,
  taskNode: TaskNode,
}

interface AgentListItem {
  id: string
  role: string
  goal: string
  backstory: string
  allowed_tools: string[]
  max_iter: number
}

interface RunResult {
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: string
  error?: string
  tokens_used?: number
}

function FlowCanvas() {
  const reactFlowInstance = useReactFlow()
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [running, setRunning] = useState(false)
  const [runResults, setRunResults] = useState<Record<string, RunResult>>({})
  const [previewCode, setPreviewCode] = useState('')
  const [codeDialogOpen, setCodeDialogOpen] = useState(false)
  const [templatesDialogOpen, setTemplatesDialogOpen] = useState(false)
  const [exportDialogOpen, setExportDialogOpen] = useState(false)
  const [exportWarning, setExportWarning] = useState('')
  const saveRef = useRef(false)
  const snapshotRestored = useRef(false)

  const orgId = useMemo(() => {
    if (typeof window === 'undefined') return ''
    return localStorage.getItem('organization_id') || localStorage.getItem('selected_org_id') || ''
  }, [])

  const { data: agentsData, isLoading: agentsLoading, isError: agentsError } = useQuery<{ agents: AgentListItem[] }>({
    queryKey: ['agents-list', orgId],
    queryFn: () => api.get('/agents?active_only=true'),
    staleTime: 30000,
  })

  useEffect(() => {
    if (snapshotRestored.current) return
    snapshotRestored.current = true
    try {
      const saved = localStorage.getItem(LOCALSTORAGE_KEY)
      if (saved) {
        const restored = snapshotToNodes(saved)
        if (restored && restored.nodes.length > 0) {
          setNodes(restored.nodes)
          setEdges(restored.edges)
        }
      }
    } catch {
      // Snapshot corrupt, start fresh
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- snapshot restore only on mount
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      if (nodes.length > 0) {
        const snapshot = nodesToSnapshot(nodes, edges)
        localStorage.setItem(LOCALSTORAGE_KEY, snapshot)
      }
    }, AUTOSAVE_INTERVAL)
    return () => clearInterval(interval)
  }, [nodes, edges])

  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault()
      const raw = event.dataTransfer.getData('application/reactflow')
      if (!raw) return
      let agent: AgentListItem
      try {
        agent = JSON.parse(raw)
      } catch {
        return
      }

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      })

      const nodeId = `agent_${agent.role}_${Date.now()}`
      const newNode: Node = {
        id: nodeId,
        type: 'agentNode',
        position,
        data: {
          role: agent.role,
          goal: agent.goal,
          tools: agent.allowed_tools,
          backstory: agent.backstory,
          maxIter: agent.max_iter,
        },
      }

      setNodes((nds) => nds.concat(newNode))
    },
    [reactFlowInstance, setNodes],
  )

  const onConnect = useCallback(
    (params: Connection) => {
      if (!params.source || !params.target) return

      const sourceNode = nodes.find((n) => n.id === params.source)
      const targetNode = nodes.find((n) => n.id === params.target)

      if (!sourceNode || !targetNode) return

      const valid =
        (sourceNode.type === 'agentNode' && targetNode.type === 'taskNode') ||
        (sourceNode.type === 'taskNode' && targetNode.type === 'taskNode')

      if (!valid) {
        toast.error('Invalid connection: only agent->task or task->task allowed')
        return
      }

      setEdges((eds) =>
        addEdge({ ...params, animated: true, style: { stroke: '#555' } }, eds),
      )
    },
    [nodes, setEdges],
  )

  function handleAddTask() {
    const taskId = `task_${Date.now()}`
    const newNode: Node = {
      id: taskId,
      type: 'taskNode',
      position: { x: 400, y: 100 + nodes.filter((n) => n.type === 'taskNode').length * 120 },
      data: {
        description: '',
        expectedOutput: '',
        assignedAgent: '',
      },
    }
    setNodes((nds) => nds.concat(newNode))
  }

  function handleExport() {
    const agentNodes = nodes.filter((n) => n.type === 'agentNode')
    if (agentNodes.length === 0) {
      toast.error('Add at least one agent to export')
      return
    }

    const roles = agentNodes.map((n) => (n.data as Record<string, unknown>).role as string)
    const duplicates = roles.filter((r, i) => roles.indexOf(r) !== i)
    if (duplicates.length > 0) {
      toast.error(`Duplicate roles: ${Array.from(new Set(duplicates)).join(', ')}`)
      return
    }

    setExportWarning('Tasks and connections not exported (bundle-schema-v2.md limitation). Use Copy as JSON for complete graph.')
    setExportDialogOpen(true)
  }

  async function confirmExport() {
    try {
      const payload = canvasToExportPayload(nodes)
      const supabase = createClient()
      const { data: { session } } = await supabase.auth.getSession()
      const orgId = typeof window !== 'undefined'
        ? localStorage.getItem('organization_id') || localStorage.getItem('selected_org_id') || ''
        : ''
      const response = await fetch(`${process.env.NEXT_PUBLIC_FASTAPI_URL}/bundles/export`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
          'X-Org-ID': orgId,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ bundle_name: 'crew_export', agents: payload.agents }),
      })
      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || `Export failed: ${response.status}`)
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'crew_export.zip'
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Crew exported as ZIP')
      setExportDialogOpen(false)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Export failed'
      toast.error(message)
    }
  }

  async function handleRunAll() {
    const agentNodes = nodes.filter((n) => n.type === 'agentNode')
    if (agentNodes.length === 0) {
      toast.error('No agents on canvas')
      return
    }

    setRunning(true)
    const results: Record<string, RunResult> = {}
    setRunResults({ ...results })

    for (const node of agentNodes) {
      const data = node.data as Record<string, unknown>
      const role = (data.role as string) || ''
      if (!role) continue

      const taskEdges = edges.filter((e) => e.source === node.id)
      const connectedTasks = taskEdges
        .map((e) => nodes.find((n) => n.id === e.target))
        .filter((n): n is Node => n !== undefined && n.type === 'taskNode')
      const taskDescription = connectedTasks.length > 0
        ? (connectedTasks[0].data as Record<string, unknown>).description as string || 'Execute your assigned task'
        : 'Execute your assigned task'

      const encodedRole = encodeURIComponent(role)
      results[role] = { status: 'running' }
      setRunResults({ ...results })

      try {
        const runResp = await api.post(`/agents/${encodedRole}/run`, { input_data: { message: taskDescription } })
        const taskId = runResp.task_id

        let status = 'pending'
        const maxPolls = 60
        for (let poll = 0; poll < maxPolls; poll++) {
          await new Promise((r) => setTimeout(r, 2000))
          const taskResp = await api.get(`/tasks/${taskId}`)
          status = taskResp.status
          if (status === 'completed' || status === 'failed') {
            results[role] = {
              status: status as 'completed' | 'failed',
              result: taskResp.result ? String(taskResp.result) : undefined,
              error: taskResp.error,
              tokens_used: taskResp.tokens_used,
            }
            setRunResults({ ...results })
            break
          }
        }
        if (status !== 'completed' && status !== 'failed') {
          results[role] = { status: 'failed', error: 'Timeout after 120s' }
          setRunResults({ ...results })
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Execution failed'
        results[role] = { status: 'failed', error: message }
        setRunResults({ ...results })
      }
    }

    setRunning(false)
    toast.success('Run All completed')
  }

  function handlePreviewCode() {
    const code = generateCrewPy(nodes, edges)
    setPreviewCode(code)
    setCodeDialogOpen(true)
  }

  function handleSaveCrew() {
    const snapshot = nodesToSnapshot(nodes, edges)
    localStorage.setItem(LOCALSTORAGE_KEY, snapshot)

    if (nodes.length === 0) {
      toast.info('Canvas is empty. Nothing to save.')
      return
    }

    const blob = new Blob([snapshot], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `crew_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)

    toast.success('Crew saved to localStorage and downloaded')
    saveRef.current = true
  }

  function handleLoadTemplate(index: number) {
    const template = CREW_TEMPLATES[index]
    if (!template) return
    setNodes(template.nodes.map((n) => ({ ...n })))
    setEdges(template.edges.map((e) => ({ ...e, animated: true, style: { stroke: '#555' } })))
    setTemplatesDialogOpen(false)
    toast.success(`Loaded template: ${template.name}`)
  }

  function handleCopyJSON() {
    const snapshot = nodesToSnapshot(nodes, edges)
    navigator.clipboard.writeText(snapshot)
    toast.success('Full graph copied to clipboard as JSON')
  }

  const sidebarAgents = agentsData?.agents ?? []

  const duplicatedRoles = (() => {
    const agentNodes = nodes.filter((n) => n.type === 'agentNode')
    const roles = agentNodes.map((n) => (n.data as Record<string, unknown>).role as string).filter(Boolean)
    const seen = new Set<string>()
    const dups = new Set<string>()
    roles.forEach((r) => {
      if (seen.has(r)) dups.add(r)
      seen.add(r)
    })
    return dups
  })()

  const hasAgentNodes = nodes.some((n) => n.type === 'agentNode')
  const exportDisabled = !hasAgentNodes || duplicatedRoles.size > 0

  const nodesWithWarnings = nodes
    .filter((n) => n.type === 'agentNode')
    .filter((n) => !edges.some((e) => e.source === n.id))
    .map((n) => n.id)

  return (
    <div className="flex h-full w-full">
      <div className="w-56 shrink-0 border-r bg-muted/20 flex flex-col">
        <div className="px-3 py-2 border-b">
          <span className="text-xs font-semibold">Agent Palette</span>
        </div>
        <ScrollArea className="flex-1">
          {agentsLoading && (
            <div className="p-3 space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          )}
          {agentsError && (
            <div className="p-3 text-xs text-muted-foreground">
              Failed to load agents. Check backend connection.
            </div>
          )}
          {!agentsLoading && !agentsError && sidebarAgents.length === 0 && (
            <div className="p-3 text-center text-xs text-muted-foreground">
              <p>No agents yet.</p>
              <p className="mt-1">Create one in Agent Form first.</p>
            </div>
          )}
          {!agentsLoading && sidebarAgents.map((agent) => (
            <div
              key={agent.id}
              className="mx-2 my-1 p-2 rounded-md border bg-card cursor-grab active:cursor-grabbing hover:bg-accent text-xs"
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData('application/reactflow', JSON.stringify(agent))
                e.dataTransfer.effectAllowed = 'move'
              }}
            >
              <div className="font-semibold truncate">{agent.role}</div>
              <div className="text-muted-foreground line-clamp-1 mt-0.5">{agent.goal || 'No goal'}</div>
              <div className="text-[10px] text-muted-foreground mt-1">
                {agent.allowed_tools.length} tool{agent.allowed_tools.length !== 1 ? 's' : ''}
              </div>
            </div>
          ))}
        </ScrollArea>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center justify-between border-b px-4 py-2 bg-muted/10">
          <span className="text-sm font-medium">Crew Canvas</span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={handleAddTask}
              disabled={running}
            >
              <Plus className="mr-1 h-3.5 w-3.5" />
              Add Task
            </Button>
            <Separator orientation="vertical" className="h-6 mx-0.5" />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setTemplatesDialogOpen(true)}
              disabled={running}
            >
              <Layers className="mr-1 h-3.5 w-3.5" />
              Templates
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreviewCode}
            >
              <Code className="mr-1 h-3.5 w-3.5" />
              Preview Code
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleSaveCrew}
              disabled={running}
            >
              <Save className="mr-1 h-3.5 w-3.5" />
              Save Crew
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={exportDisabled || running}
              title={exportDisabled ? (duplicatedRoles.size > 0 ? 'Duplicate roles detected' : 'Add at least one agent') : undefined}
            >
              <Download className="mr-1 h-3.5 w-3.5" />
              Export
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleRunAll}
              disabled={!hasAgentNodes || running}
            >
              <Play className="mr-1 h-3.5 w-3.5" />
              Run All
            </Button>
          </div>
        </div>
        <div className="flex-1" onDragOver={onDragOver} onDrop={onDrop}>
          <ReactFlow
            nodes={nodes.map((n) => {
              const isWarning = nodesWithWarnings.includes(n.id)
              return {
                ...n,
                className: isWarning ? 'border-yellow-500' : undefined,
                style: isWarning ? { ...n.style, border: '2px solid rgb(234 179 8)', borderRadius: '8px' } : n.style,
              }
            })}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            deleteKeyCode={['Backspace', 'Delete']}
            multiSelectionKeyCode={'Shift'}
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
      </div>

      {Object.keys(runResults).length > 0 && (
        <div className="w-72 shrink-0 border-l bg-muted/10 flex flex-col">
          <div className="px-3 py-2 border-b">
            <span className="text-xs font-semibold">Run Results</span>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-2">
              {Object.entries(runResults).map(([role, result]) => (
                <div key={role} className="p-2 rounded-md border bg-card text-xs">
                  <div className="font-semibold flex items-center gap-1">
                    <span>{role}</span>
                    {result.status === 'running' && <LoadingSpinner size="sm" />}
                    {result.status === 'completed' && (
                      <span className="text-green-600 ml-1">&#10003;</span>
                    )}
                    {result.status === 'failed' && (
                      <span className="text-red-600 ml-1">&#10007;</span>
                    )}
                  </div>
                  {result.status === 'completed' && result.result && (
                    <p className="mt-1 text-muted-foreground line-clamp-3">{result.result}</p>
                  )}
                  {result.status === 'failed' && result.error && (
                    <p className="mt-1 text-red-500">{result.error}</p>
                  )}
                  {result.tokens_used !== undefined && (
                    <p className="mt-1 text-[10px] text-muted-foreground">
                      Tokens: {result.tokens_used}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      <Dialog open={codeDialogOpen} onOpenChange={setCodeDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Code className="h-5 w-5" />
              Generated Python Code
            </DialogTitle>
          </DialogHeader>
          <pre className="bg-muted rounded-md p-4 text-xs overflow-x-auto whitespace-pre font-mono">
            {previewCode || '# No agents or tasks on canvas'}
          </pre>
        </DialogContent>
      </Dialog>

      <Dialog open={templatesDialogOpen} onOpenChange={setTemplatesDialogOpen}>
        <DialogContent className="max-w-xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              Crew Templates
            </DialogTitle>
            <DialogDescription>
              Choose a preset to populate the canvas.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            {CREW_TEMPLATES.map((template, i) => (
              <div
                key={template.id}
                className="flex items-center justify-between p-3 rounded-md border hover:bg-accent cursor-pointer"
                onClick={() => handleLoadTemplate(i)}
              >
                <div>
                  <p className="text-sm font-semibold">{template.name}</p>
                  <p className="text-xs text-muted-foreground">{template.description}</p>
                </div>
                <span className="text-[10px] bg-muted px-2 py-0.5 rounded-full">
                  {template.category}
                </span>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={exportDialogOpen} onOpenChange={setExportDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              Export Crew
            </DialogTitle>
            <DialogDescription className="space-y-3">
              <p className="text-yellow-600 dark:text-yellow-400 text-sm">
                {exportWarning}
              </p>
              <div className="flex gap-2 pt-2">
                <Button variant="default" onClick={confirmExport}>
                  Export as ZIP
                </Button>
                <Button variant="outline" onClick={handleCopyJSON}>
                  <Share2 className="mr-1.5 h-4 w-4" />
                  Copy as JSON
                </Button>
              </div>
            </DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export function CrewCanvas() {
  return (
    <ReactFlowProvider>
      <FlowCanvas />
    </ReactFlowProvider>
  )
}
