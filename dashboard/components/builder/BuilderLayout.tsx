'use client'

import { useState } from 'react'

import { BuilderCanvas } from '@/components/builder/BuilderCanvas'
import { BuilderErrorBoundary } from '@/components/builder/BuilderErrorBoundary'
import { AgentForm, type AgentFormData } from '@/components/builder/AgentForm'
import { TemplatePicker } from '@/components/builder/TemplatePicker'
import { AgentPlayground } from '@/components/builder/AgentPlayground'
import { useBuilderTab } from '@/components/builder/BuilderTabContext'
import type { TemplateDetail } from '@/components/builder/TemplatePicker'
import { mapTemplateToFormValues } from '@/lib/template-mapper'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Layers, Play, Wand2, Network } from 'lucide-react'

export function BuilderLayout() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [playgroundOpen, setPlaygroundOpen] = useState(false)
  const [templateData, setTemplateData] = useState<AgentFormData | null>(null)
  const [currentRole, setCurrentRole] = useState<string | null>(null)
  const { activeTab, setActiveTab } = useBuilderTab()

  function handleSelectTemplate(template: TemplateDetail) {
    const mapped = mapTemplateToFormValues(template)
    setTemplateData(mapped)
    setDialogOpen(false)
  }

  function handleClear() {
    setTemplateData(null)
  }

  function handleRoleChange(role: string) {
    setCurrentRole(role || null)
  }

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
      <div className="flex items-center justify-between px-1 pb-2">
        <TabsList>
          <TabsTrigger value="agent-form" className="flex items-center gap-1.5">
            <Wand2 className="h-4 w-4" />
            Agent Form
          </TabsTrigger>
          <TabsTrigger value="crew-canvas" className="flex items-center gap-1.5">
            <Network className="h-4 w-4" />
            Crew Canvas
          </TabsTrigger>
        </TabsList>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPlaygroundOpen(true)}
            disabled={!currentRole}
          >
            <Play className="mr-1.5 h-4 w-4" />
            Playground
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDialogOpen(true)}
          >
            <Layers className="mr-1.5 h-4 w-4" />
            Templates
          </Button>
        </div>
      </div>

      <TabsContent value="agent-form" className="flex-1 mt-0 data-[state=inactive]:hidden">
        <div className="grid h-full gap-4 lg:grid-cols-[60%_40%]">
          <div className="min-h-0">
            <BuilderErrorBoundary>
              <BuilderCanvas />
            </BuilderErrorBoundary>
          </div>
          <div className="flex flex-col overflow-hidden rounded-lg border bg-card p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Agent Configuration</h3>
            </div>
            <div className="flex-1 overflow-y-auto">
              <AgentForm
                templateData={templateData}
                onClear={handleClear}
                onRoleChange={handleRoleChange}
              />
            </div>
          </div>
        </div>
      </TabsContent>

      <TabsContent value="crew-canvas" className="flex-1 mt-0 data-[state=inactive]:hidden">
        <BuilderErrorBoundary>
          <BuilderCanvas />
        </BuilderErrorBoundary>
      </TabsContent>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              Template Library
            </DialogTitle>
          </DialogHeader>
          <TemplatePicker onSelect={handleSelectTemplate} />
        </DialogContent>
      </Dialog>

      <Sheet open={playgroundOpen} onOpenChange={setPlaygroundOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md flex flex-col p-4">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              Agent Playground
            </SheetTitle>
          </SheetHeader>
          {currentRole && <AgentPlayground role={currentRole} />}
        </SheetContent>
      </Sheet>
    </Tabs>
  )
}
