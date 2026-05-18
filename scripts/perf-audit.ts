#!/usr/bin/env npx tsx

interface AuditResult {
  file: string
  line: number
  type: 'inline-click-outside' | 'missing-use-memo' | 'sync-css-import'
  description: string
}

function parseArgs(): string {
  const args = process.argv.slice(2)
  const pathIndex = args.indexOf('--path')
  if (pathIndex !== -1 && args[pathIndex + 1]) {
    return args[pathIndex + 1]
  }
  return 'dashboard/components/builder'
}

async function main() {
  const targetDir = parseArgs()
  const results: AuditResult[] = []

  const fs = await import('fs/promises')
  const path = await import('path')

  async function walkDir(dir: string): Promise<string[]> {
    const entries = await fs.readdir(dir, { withFileTypes: true })
    const files: string[] = []
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name)
      if (entry.isDirectory() && entry.name !== 'node_modules' && entry.name !== '.next') {
        files.push(...await walkDir(fullPath))
      } else if (entry.isFile() && (entry.name.endsWith('.tsx') || entry.name.endsWith('.ts'))) {
        files.push(fullPath)
      }
    }
    return files
  }

  const files = await walkDir(targetDir)

  for (const file of files) {
    const content = await fs.readFile(file, 'utf-8')
    const lines = content.split('\n')

    for (let i = 0; i < lines.length; i++) {
      const lineNum = i + 1
      const line = lines[i]

      if (
        line.includes('useEffect') &&
        (line.includes('mousedown') || lines[i + 1]?.includes('mousedown'))
      ) {
        results.push({
          file,
          line: lineNum,
          type: 'inline-click-outside',
          description: 'Inline mousedown listener en useEffect — deberia usar useClickOutside hook',
        })
      }

      if (
        line.includes("import 'reactflow/dist/style.css'") ||
        line.includes("import 'reactflow/dist/base.css'")
      ) {
        results.push({
          file,
          line: lineNum,
          type: 'sync-css-import',
          description: 'Import sincrono de CSS de libreria grande — deberia cargarse dinamicamente via useEffect',
        })
      }
    }

    const useEffectMatches = content.match(/useEffect/g)
    const useMemoMatches = content.match(/useMemo/g)
    const callbackPattern = /\.(filter|map|reduce|find|some|every)\(/g
    const callbackMatches = content.match(callbackPattern)

    if (
      useEffectMatches &&
      callbackMatches &&
      useMemoMatches &&
      callbackMatches.length > useMemoMatches.length + 5
    ) {
      results.push({
        file,
        line: 0,
        type: 'missing-use-memo',
        description: `Posible calculo derivado sin memoizar: ${callbackMatches.length} callbacks de array vs ${useMemoMatches.length} useMemo`,
      })
    }
  }

  if (results.length === 0) {
    console.log('✅ No se detectaron regresiones de performance.')
    process.exit(0)
  }

  console.log(`⚠️  Se detectaron ${results.length} problema(s) de performance:\n`)
  for (const r of results) {
    const loc = r.line > 0 ? `:${r.line}` : ''
    console.log(`  [${r.type}] ${r.file}${loc}`)
    console.log(`    ${r.description}\n`)
  }

  const blocker = results.some((r) => r.type === 'inline-click-outside' || r.type === 'sync-css-import')
  if (blocker) {
    console.log('❌ Hay regresiones bloqueantes. Corregir antes de commit.')
    process.exit(1)
  }

  console.log('⚠️  Regresiones no bloqueantes detectadas. Revisar antes de commit.')
  process.exit(0)
}

main().catch((err) => {
  console.error('Error ejecutando perf-audit:', err)
  process.exit(1)
})
