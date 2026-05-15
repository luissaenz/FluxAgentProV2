import type { Node, Edge } from 'reactflow'

export function generateCrewPy(nodes: Node[], edges: Edge[]): string {
  const agentNodes = nodes.filter((n) => n.type === 'agentNode')
  const taskNodes = nodes.filter((n) => n.type === 'taskNode')

  const agentVarMap: Record<string, string> = {}
  const lines: string[] = []

  lines.push('from crewai import Agent, Task, Crew, Process')
  lines.push('')

  agentNodes.forEach((node, i) => {
    const data = node.data as Record<string, unknown>
    const varName = `agent_${i}`
    agentVarMap[node.id] = varName
    const role = ((data.role as string) || 'unnamed').replace(/'/g, "\\'")
    const goal = ((data.goal as string) || '').replace(/'/g, "\\'")
    const backstory = ((data.backstory as string) || '').replace(/'/g, "\\'")
    const tools = Array.isArray(data.tools) ? (data.tools as string[]) : []

    lines.push(`${varName} = Agent(`)
    lines.push(`    role='${role}',`)
    lines.push(`    goal='${goal}',`)
    lines.push(`    backstory='${backstory}',`)
    if (tools.length > 0) {
      const toolsStr = tools.map((t) => `'${t}'`).join(', ')
      lines.push(`    tools=[${toolsStr}],`)
    }
    lines.push(`    allow_code_execution=False,`)
    lines.push(`)`)
    lines.push('')
  })

  const agentEdgeMap: Record<string, string> = {}
  edges.forEach((edge) => {
    const sourceNode = nodes.find((n) => n.id === edge.source)
    const targetNode = nodes.find((n) => n.id === edge.target)
    if (sourceNode?.type === 'agentNode' && targetNode?.type === 'taskNode') {
      agentEdgeMap[edge.target] = edge.source
    }
  })

  taskNodes.forEach((node, i) => {
    const data = node.data as Record<string, unknown>
    const varName = `task_${i}`
    const description = ((data.description as string) || 'Execute task').replace(/'/g, "\\'")
    const expectedOutput = ((data.expectedOutput as string) || 'Result').replace(/'/g, "\\'")
    const assignedSource = agentEdgeMap[node.id]
    const assignedVar = assignedSource ? agentVarMap[assignedSource] : null

    lines.push(`${varName} = Task(`)
    lines.push(`    description='${description}',`)
    lines.push(`    expected_output='${expectedOutput}',`)
    if (assignedVar) {
      lines.push(`    agent=${assignedVar},`)
    }
    lines.push(`)`)
    lines.push('')
  })

  const agentVars = Object.values(agentVarMap)
  const taskVars = taskNodes.map((_, i) => `task_${i}`)

  if (agentVars.length > 0 || taskVars.length > 0) {
    lines.push('crew = Crew(')
    if (agentVars.length > 0) {
      lines.push(`    agents=[${agentVars.join(', ')}],`)
    }
    if (taskVars.length > 0) {
      lines.push(`    tasks=[${taskVars.join(', ')}],`)
    }
    lines.push('    process=Process.sequential,')
    lines.push(')')
    lines.push('')
    lines.push('result = crew.kickoff()')
  }

  return lines.join('\n')
}
