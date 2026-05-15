import type { Node, Edge } from 'reactflow'

export interface CrewTemplate {
  id: string
  name: string
  description: string
  category: string
  nodes: Node[]
  edges: Edge[]
}

export const CREW_TEMPLATES: CrewTemplate[] = [
  {
    id: 'research-pipeline',
    name: 'Research Pipeline',
    description: 'Researcher agent searches for information and compiles a report.',
    category: 'Research',
    nodes: [
      {
        id: 'r1',
        type: 'agentNode',
        position: { x: 100, y: 100 },
        data: { role: 'researcher', goal: 'Research a given topic thoroughly and compile findings', tools: ['web_search'], backstory: 'Expert researcher with deep analytical skills' },
      },
      {
        id: 't1',
        type: 'taskNode',
        position: { x: 400, y: 100 },
        data: { description: 'Search and gather information', expectedOutput: 'Research summary with key findings', assignedAgent: 'researcher' },
      },
    ],
    edges: [
      {
        id: 'e-r1-t1',
        source: 'r1',
        target: 't1',
        sourceHandle: 'bottom',
        targetHandle: 'left',
        animated: true,
      },
    ],
  },
  {
    id: 'code-review-crew',
    name: 'Code Review Crew',
    description: 'Reviewer analyzes code for bugs and best practices, then generates a report.',
    category: 'Development',
    nodes: [
      {
        id: 'cr1',
        type: 'agentNode',
        position: { x: 100, y: 100 },
        data: { role: 'code_reviewer', goal: 'Review code for bugs, security issues, and best practices', tools: ['code_analysis'], backstory: 'Senior software engineer with deep expertise' },
      },
      {
        id: 'ct1',
        type: 'taskNode',
        position: { x: 400, y: 100 },
        data: { description: 'Analyze code quality and security', expectedOutput: 'Code review report with recommendations', assignedAgent: 'code_reviewer' },
      },
    ],
    edges: [
      {
        id: 'e-cr1-ct1',
        source: 'cr1',
        target: 'ct1',
        sourceHandle: 'bottom',
        targetHandle: 'left',
        animated: true,
      },
    ],
  },
  {
    id: 'content-creation',
    name: 'Content Creation',
    description: 'Writer drafts content and Editor polishes the final version.',
    category: 'General',
    nodes: [
      {
        id: 'w1',
        type: 'agentNode',
        position: { x: 100, y: 100 },
        data: { role: 'writer', goal: 'Write engaging and accurate content on any topic', tools: ['web_search'], backstory: 'Creative writer with excellent communication skills' },
      },
      {
        id: 'e1',
        type: 'agentNode',
        position: { x: 100, y: 250 },
        data: { role: 'editor', goal: 'Edit and polish content for clarity and accuracy', tools: [], backstory: 'Meticulous editor with attention to detail' },
      },
      {
        id: 'ct1',
        type: 'taskNode',
        position: { x: 400, y: 100 },
        data: { description: 'Draft initial article', expectedOutput: 'First draft article', assignedAgent: 'writer' },
      },
      {
        id: 'ct2',
        type: 'taskNode',
        position: { x: 400, y: 250 },
        data: { description: 'Review and edit article', expectedOutput: 'Final polished article', assignedAgent: 'editor' },
      },
    ],
    edges: [
      {
        id: 'e-w1-ct1',
        source: 'w1',
        target: 'ct1',
        sourceHandle: 'bottom',
        targetHandle: 'left',
        animated: true,
      },
      {
        id: 'e-e1-ct2',
        source: 'e1',
        target: 'ct2',
        sourceHandle: 'bottom',
        targetHandle: 'left',
        animated: true,
      },
    ],
  },
  {
    id: 'data-analysis',
    name: 'Data Analysis',
    description: 'Analyst parses data and creates visualizations with insights.',
    category: 'Research',
    nodes: [
      {
        id: 'a1',
        type: 'agentNode',
        position: { x: 100, y: 100 },
        data: { role: 'analyst', goal: 'Analyze data and extract meaningful insights', tools: ['python_repl'], backstory: 'Data scientist with expertise in statistical analysis' },
      },
      {
        id: 'dt1',
        type: 'taskNode',
        position: { x: 400, y: 100 },
        data: { description: 'Parse and clean dataset', expectedOutput: 'Clean structured data ready for analysis', assignedAgent: 'analyst' },
      },
      {
        id: 'dt2',
        type: 'taskNode',
        position: { x: 400, y: 250 },
        data: { description: 'Generate visualization report', expectedOutput: 'Charts and key insights summary', assignedAgent: 'analyst' },
      },
    ],
    edges: [
      {
        id: 'e-a1-dt1',
        source: 'a1',
        target: 'dt1',
        sourceHandle: 'bottom',
        targetHandle: 'left',
        animated: true,
      },
      {
        id: 'e-a1-dt2',
        source: 'a1',
        target: 'dt2',
        sourceHandle: 'bottom',
        targetHandle: 'left',
        animated: true,
      },
    ],
  },
]
