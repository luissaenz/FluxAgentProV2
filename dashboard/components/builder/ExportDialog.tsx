'use client'

import { useState, useMemo } from 'react'
import { toast } from 'sonner'
import {
  Download,
  Share2,
  AlertTriangle,
  Info,
  FileArchive,
  Inbox,
} from 'lucide-react'

import { fapDownload } from '@/lib/api'
import { MAX_EXPORT_AGENTS } from '@/lib/constants'
import type { AgentExportItem, ExportBundleRequest } from '@/lib/types'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from '@/components/ui/tooltip'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'

export interface ExportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  agents: AgentExportItem[]
  source: 'agent-form' | 'crew-canvas'
  bundleName?: string
  enableSkills?: boolean
  fullGraphJson?: string
  onExportComplete?: () => void
}

function generateDefaultBundleName(): string {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `export_${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
}

export function ExportDialog({
  open,
  onOpenChange,
  agents,
  source,
  bundleName: initialBundleName,
  enableSkills = false,
  fullGraphJson,
  onExportComplete,
}: ExportDialogProps) {
  const [includeSkills, setIncludeSkills] = useState(false)
  const [bundleNameInput, setBundleNameInput] = useState(initialBundleName ?? generateDefaultBundleName())
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fileSize, setFileSize] = useState<string | null>(null)
  const [exportedFilename, setExportedFilename] = useState<string | null>(null)

  const isCrewCanvas = source === 'crew-canvas'
  const exceedsLimit = agents.length > MAX_EXPORT_AGENTS
  const isEmpty = agents.length === 0

  const exportDisabled = isExporting || exceedsLimit || isEmpty

  const warnings = useMemo(() => {
    const w: string[] = []
    if (isCrewCanvas) {
      w.push('LLM configuration not included. Use Agent Form export for full config.')
      w.push('Tasks and connections not exported (bundle-schema-v2 limitation). Use Copy as JSON for full graph.')
    }
    return w
  }, [isCrewCanvas])

  const [showTextarea, setShowTextarea] = useState(false)

  function handleCopyJSON() {
    if (!fullGraphJson) {
      toast.error('No JSON data to copy')
      return
    }
    try {
      navigator.clipboard.writeText(fullGraphJson)
      toast.success('JSON copied to clipboard')
    } catch {
      setShowTextarea(true)
    }
  }

  function handleManualCopy() {
    if (!fullGraphJson) return
    try {
      navigator.clipboard.writeText(fullGraphJson)
      toast.success('JSON copied to clipboard')
    } catch {
      toast.error('Clipboard still unavailable. Select all and copy manually.')
    }
  }

  async function handleExport() {
    if (exportDisabled) return

    setError(null)
    setFileSize(null)
    setExportedFilename(null)
    setIsExporting(true)

    const payload: ExportBundleRequest = {
      bundle_name: bundleNameInput || generateDefaultBundleName(),
      agents: agents.slice(0, MAX_EXPORT_AGENTS),
    }

    if (includeSkills && enableSkills) {
      payload.skills = []
    }

    try {
      const response = await fapDownload('/bundles/export', payload)
      const blob = await response.blob()
      const sizeFormatted = blob.size < 1024
        ? `${blob.size} B`
        : blob.size < 1024 * 1024
          ? `${(blob.size / 1024).toFixed(1)} KB`
          : `${(blob.size / (1024 * 1024)).toFixed(1)} MB`

      const filename = `${payload.bundle_name}.zip`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)

      setFileSize(sizeFormatted)
      setExportedFilename(filename)
      toast.success(`Exported as ${filename} (${sizeFormatted})`)
      onExportComplete?.()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Export failed'
      setError(message)
      toast.error(message)
    } finally {
      setIsExporting(false)
    }
  }

  function handleOpenChange(open: boolean) {
    if (!open) {
      setError(null)
      setFileSize(null)
      setExportedFilename(null)
      setBundleNameInput(initialBundleName ?? generateDefaultBundleName())
    }
    onOpenChange(open)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileArchive className="h-5 w-5" />
            Export {isCrewCanvas ? 'Crew' : 'Agent'}
          </DialogTitle>
          <DialogDescription className="space-y-3">
            {warnings.length > 0 && (
              <div className="space-y-1">
                {warnings.map((w, i) => (
                  <p key={i} className="flex items-start gap-1.5 text-yellow-600 dark:text-yellow-400 text-xs">
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                    <span>{w}</span>
                  </p>
                ))}
              </div>
            )}
          </DialogDescription>
        </DialogHeader>

        {isEmpty ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Inbox className="h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground">No agents to export</p>
            <DialogFooter className="mt-4">
              <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
            </DialogFooter>
          </div>
        ) : (
          <>
            <div className="space-y-3">
              {agents.slice(0, MAX_EXPORT_AGENTS).map((agent, i) => {
                const goalStr = typeof agent.soul_json?.goal === 'string'
                  ? agent.soul_json.goal
                  : ''
                const truncatedGoal = goalStr.length > 60 ? goalStr.slice(0, 60) + '...' : goalStr
                return (
                  <div key={i} className="flex items-start justify-between p-2 rounded-md border text-xs">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold truncate">{agent.role || '(unnamed)'}</p>
                      {truncatedGoal && (
                        <p className="text-muted-foreground line-clamp-1 mt-0.5">{truncatedGoal}</p>
                      )}
                      <p className="text-[10px] text-muted-foreground mt-1">
                        {agent.allowed_tools.length} tool{agent.allowed_tools.length !== 1 ? 's' : ''}
                        {' · '}max iter: {agent.max_iter}
                      </p>
                    </div>
                  </div>
                )
              })}
              {agents.length > MAX_EXPORT_AGENTS && (
                <p className="text-xs text-destructive flex items-center gap-1">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  +{agents.length - MAX_EXPORT_AGENTS} agents not shown ({MAX_EXPORT_AGENTS} agents limit)
                </p>
              )}
            </div>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="bundleName" className="text-xs">Bundle Name</Label>
                <Input
                  id="bundleName"
                  value={bundleNameInput}
                  onChange={(e) => setBundleNameInput(e.target.value)}
                  disabled={isExporting}
                  className="h-8 text-xs"
                />
              </div>

              <div className="flex items-center space-x-2">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="flex items-center space-x-2">
                        <Checkbox
                          checked={includeSkills}
                          onCheckedChange={(v) => setIncludeSkills(v === true)}
                          disabled={!enableSkills || isExporting}
                          id="includeSkills"
                        />
                        <Label
                          htmlFor="includeSkills"
                          className={`text-xs ${!enableSkills ? 'text-muted-foreground cursor-not-allowed' : 'cursor-pointer'}`}
                        >
                          Include skills
                        </Label>
                      </span>
                    </TooltipTrigger>
                    {!enableSkills && (
                      <TooltipContent side="top">
                        Coming soon — custom skill selector not available yet.
                      </TooltipContent>
                    )}
                  </Tooltip>
                </TooltipProvider>
              </div>

              {exceedsLimit && (
                <p className="text-xs text-destructive flex items-center gap-1">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  +{MAX_EXPORT_AGENTS} agents limit reached
                </p>
              )}

              {error && (
                <div className="rounded-md bg-destructive/10 p-3 text-xs text-destructive">
                  <p className="font-semibold">Export failed</p>
                  <p>{error}</p>
                </div>
              )}

              {exportedFilename && fileSize && (
                <div className="rounded-md bg-green-50 dark:bg-green-950/20 p-3 text-xs text-green-700 dark:text-green-300">
                  <p className="font-semibold flex items-center gap-1">
                    <Info className="h-3.5 w-3.5" />
                    Exported as {exportedFilename} ({fileSize})
                  </p>
                </div>
              )}
            </div>

            {showTextarea && fullGraphJson && (
              <div className="space-y-2">
                <Label className="text-xs">Full JSON (clipboard unavailable)</Label>
                <Textarea
                  readOnly
                  value={fullGraphJson}
                  className="h-40 font-mono text-xs"
                />
                <Button variant="outline" size="sm" onClick={handleManualCopy}>
                  <Share2 className="mr-1.5 h-3 w-3" />
                  Copy
                </Button>
              </div>
            )}

            <DialogFooter className="gap-2">
              {isExporting ? (
                <div className="flex items-center gap-2 w-full justify-end">
                  <LoadingSpinner size="sm" label="Generating bundle..." />
                </div>
              ) : (
                <>
                  {error && (
                    <Button variant="outline" size="sm" onClick={handleExport} disabled={exceedsLimit || isEmpty}>
                      Retry
                    </Button>
                  )}
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleExport}
                    disabled={exportDisabled}
                  >
                    <Download className="mr-1.5 h-4 w-4" />
                    Export as ZIP
                  </Button>
                  {!showTextarea && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCopyJSON}
                      disabled={isExporting}
                    >
                      <Share2 className="mr-1.5 h-4 w-4" />
                      Copy as JSON
                    </Button>
                  )}
                </>
              )}
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
