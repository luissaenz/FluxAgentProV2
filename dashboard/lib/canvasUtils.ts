import type { Node, Edge } from 'reactflow'
import type { CrewGraphNode, CrewGraphEdge, CrewGraph } from '@/lib/types'

interface AgentExportItem {
  role: string
  soul_json: Record<string, unknown>
  allowed_tools: string[]
  max_iter: number
}

function nodeToExportItem(node: Node): AgentExportItem | null {
  if (node.type !== 'agentNode') return null
  const data = node.data as Record<string, unknown>
  const role = (data.role as string) || ''
  const goal = (data.goal as string) || ''
  const backstory = (data.backstory as string) || ''
  const tools = Array.isArray(data.tools) ? (data.tools as string[]) : []
  const maxIter = typeof data.maxIter === 'number' ? data.maxIter : 3

  const soul_json: Record<string, unknown> = { goal, backstory }
  if (data.llm_provider !== undefined) soul_json.llm_provider = data.llm_provider
  if (data.llm_model !== undefined) soul_json.llm_model = data.llm_model
  if (data.verbose !== undefined) soul_json.verbose = data.verbose
  if (data.reasoning !== undefined) soul_json.reasoning = data.reasoning
  if (data.inject_date !== undefined) soul_json.inject_date = data.inject_date
  if (data.memory !== undefined) soul_json.memory = data.memory

  return {
    role,
    soul_json,
    allowed_tools: tools,
    max_iter: maxIter,
  }
}

export function canvasToExportPayload(
  nodes: Node[],
): { agents: AgentExportItem[] } {
  const agents = nodes
    .filter((n) => n.type === 'agentNode')
    .map(nodeToExportItem)
    .filter((a): a is AgentExportItem => a !== null && a.role.length > 0)
  return { agents }
}

export function nodesToSnapshot(nodes: Node[], edges: Edge[]): string {
  const graphNodes: CrewGraphNode[] = nodes.map((n) => ({
    id: n.id,
    type: (n.type === 'agentNode' || n.type === 'taskNode' ? n.type : 'agentNode') as CrewGraphNode['type'],
    data: n.data as Record<string, unknown>,
    position: n.position,
  }))

  const graphEdges: CrewGraphEdge[] = edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle ?? undefined,
    targetHandle: e.targetHandle ?? undefined,
  }))

  const graph: CrewGraph = {
    nodes: graphNodes,
    edges: graphEdges,
    metadata: {
      name: '',
      createdAt: new Date().toISOString(),
    },
  }

  return JSON.stringify(graph)
}

export function snapshotToNodes(snapshot: string): { nodes: Node[]; edges: Edge[] } | null {
  try {
    const parsed = JSON.parse(snapshot) as CrewGraph
    if (!parsed.nodes || !Array.isArray(parsed.nodes)) return null

    const nodes: Node[] = parsed.nodes
      .filter((n) => n.id && n.type && n.data && n.position)
      .map((n) => ({
        id: n.id,
        type: n.type,
        data: n.data,
        position: n.position,
      }))

    const edges: Edge[] = (parsed.edges || [])
      .filter((e) => e.id && e.source && e.target)
      .map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle,
        targetHandle: e.targetHandle,
        animated: true,
      }))

    return { nodes, edges }
  } catch {
    return null
  }
}
