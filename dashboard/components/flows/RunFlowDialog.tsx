'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useFlows, runFlow, type FlowInfo } from '@/hooks/useFlows'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Play } from 'lucide-react'

interface RunFlowDialogProps {
  children?: React.ReactNode
}

export function RunFlowDialog({ children }: RunFlowDialogProps) {
  const [open, setOpen] = useState(false)
  const [selectedFlow, setSelectedFlow] = useState<string>('')
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<{ task_id: string; status: string } | null>(null)
  const { data: flows, isLoading } = useFlows()
  const { register, handleSubmit, reset, watch } = useForm()

  const selectedFlowInfo = flows?.find(f => f.flow_type === selectedFlow)
  const inputSchema = selectedFlowInfo?.input_schema as { properties?: Record<string, { type: string; enum?: string[]; example?: string }> } | undefined

  const onSubmit = async (data: Record<string, unknown>) => {
    if (!selectedFlow) return

    setIsRunning(true)
    setResult(null)

    try {
      const res = await runFlow(selectedFlow, data)
      setResult(res)
      reset()
    } catch (error) {
      console.error('Flow execution failed:', error)
    } finally {
      setIsRunning(false)
    }
  }

  const handleClose = () => {
    setOpen(false)
    setSelectedFlow('')
    setResult(null)
    reset()
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {children || (
          <Button>
            <Play className="mr-2 h-4 w-4" />
            Ejecutar Flow
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Ejecutar Flow</DialogTitle>
          <DialogDescription>
            Selecciona un flow y completa los parámetros de entrada.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {isLoading ? (
            <LoadingSpinner label="Cargando flows..." />
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="flow_type">Flow</Label>
                <Select
                  value={selectedFlow}
                  onValueChange={(v) => {
                    setSelectedFlow(v)
                    setResult(null)
                  }}
                >
                  <SelectTrigger id="flow_type">
                    <SelectValue placeholder="Seleccionar flow..." />
                  </SelectTrigger>
                  <SelectContent>
                    {flows?.map((flow) => (
                      <SelectItem key={flow.flow_type} value={flow.flow_type}>
                        {flow.name || flow.flow_type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {inputSchema?.properties && Object.keys(inputSchema.properties).length > 0 && (
                <div className="space-y-3 max-h-64 overflow-y-auto border p-3 rounded-md">
                  {Object.entries(inputSchema.properties).map(([field, prop]) => (
                    <div key={field} className="space-y-1">
                      <Label htmlFor={field} className="capitalize">
                        {field.replace(/_/g, ' ')}
                        {selectedFlowInfo?.input_schema?.required?.includes(field) && (
                          <span className="text-destructive ml-1">*</span>
                        )}
                      </Label>
                      {prop.enum ? (
                        <Select
                          {...register(field, { required: selectedFlowInfo?.input_schema?.required?.includes(field) })}
                        >
                          <SelectTrigger id={field}>
                            <SelectValue placeholder="Seleccionar..." />
                          </SelectTrigger>
                          <SelectContent>
                            {prop.enum.map((opt) => (
                              <SelectItem key={opt} value={opt}>
                                {opt}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <Input
                          id={field}
                          type={prop.type === 'integer' ? 'number' : 'text'}
                          step={prop.type === 'integer' ? '1' : undefined}
                          placeholder={prop.example?.toString()}
                          {...register(field, { required: selectedFlowInfo?.input_schema?.required?.includes(field) })}
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}

              {result && (
                <div className="rounded-md bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/20 dark:text-green-400">
                  Flow iniciado: <span className="font-mono">{result.task_id}</span>
                </div>
              )}

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={handleClose}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={!selectedFlow || isRunning}>
                  {isRunning ? <LoadingSpinner className="mr-2 h-4 w-4" /> : null}
                  Ejecutar
                </Button>
              </div>
            </>
          )}
        </form>
      </DialogContent>
    </Dialog>
  )
}