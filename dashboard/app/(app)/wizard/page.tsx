'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useApprovals } from '@/hooks/useApprovals'
import { api } from '@/lib/api'
import { Wand2, Loader2, CheckCircle2, ArrowRight } from 'lucide-react'
import { toast } from 'sonner'

export default function AgentWizardPage() {
  const { orgId } = useCurrentOrg()
  const { data: approvals, mutate: refreshApprovals } = useApprovals(orgId)
  
  const [taskId, setTaskId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [answer, setAnswer] = useState('')
  const [status, setStatus] = useState<'idle' | 'running' | 'completed'>('idle')
  const [currentStep, setCurrentStep] = useState<any>(null)
  const [formData, setFormData] = useState<Record<string, string>>({})

  // Polling logic when running
  useEffect(() => {
    if (status !== 'running' || !taskId || currentStep) return

    const interval = setInterval(async () => {
      try {
        const task = await api.get(`/tasks/${taskId}`)
        
        if (task.status === 'completed') {
          setStatus('completed')
          clearInterval(interval)
          return
        }

        if (task.status === 'awaiting_approval' && task.approval_payload) {
          setCurrentStep({
            task_id: taskId,
            status: 'pending',
            description: task.approval_payload.question || "Responde a la solicitud",
            payload: task.approval_payload
          })
          return
        }

        const myApproval = approvals?.find(a => a.task_id === taskId && a.status === 'pending')
        if (myApproval) {
          setCurrentStep(myApproval)
        }
      } catch (err) {
        console.error("Error polling task", err)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [status, taskId, approvals, orgId, currentStep])

  const startWizard = async () => {
    setLoading(true)
    try {
      const data = await api.post('/webhooks/trigger', { flow_type: 'agent_wizard' })
      if (data.task_id) {
        setTaskId(data.task_id)
        setStatus('running')
        toast.success("Wizard iniciado correctamente")
      }
    } catch (err) {
      toast.error("Error al iniciar el wizard")
    } finally {
      setLoading(false)
    }
  }

  const sendAnswer = async () => {
    let finalAnswer = answer
    if (currentStep?.payload?.fields) {
      // Validar que todos los campos requeridos estén llenos
      const allFilled = currentStep.payload.fields.every((f: any) => formData[f.id]?.trim())
      if (!allFilled) {
        toast.error("Por favor completa todos los campos")
        return
      }
      finalAnswer = JSON.stringify(formData)
    }

    if (!finalAnswer && !currentStep?.payload?.fields) return
    
    setLoading(true)
    try {
      await api.post(`/approvals/${taskId}`, { 
        action: 'approve',
        notes: finalAnswer
      })
      setAnswer('')
      setFormData({})
      setCurrentStep(null)
      refreshApprovals()
      toast.success("Respuesta enviada")
    } catch (err) {
      toast.error("Error al enviar respuesta")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-6 p-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Wizard de Agentes</h1>
        <p className="text-muted-foreground">
          Crea perfiles de agentes deterministas mediante un flujo guiado.
        </p>
      </div>

      {status === 'idle' && (
        <Card className="border-dashed border-2 flex flex-col items-center justify-center p-12 text-center">
          <div className="bg-primary/10 p-4 rounded-full mb-4">
            <Wand2 className="w-8 h-8 text-primary" />
          </div>
          <CardTitle className="mb-2">¿Listo para crear un nuevo agente?</CardTitle>
          <CardDescription className="mb-6">
            El Wizard te guiará por 5 pasos para definir el contrato y proceso del agente.
          </CardDescription>
          <Button onClick={startWizard} disabled={loading} size="lg">
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wand2 className="mr-2 h-4 w-4" />}
            Iniciar Construcción
          </Button>
        </Card>
      )}

      {status === 'running' && (
        <Card className="relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-muted">
            <div 
              className="h-full bg-primary transition-all duration-500" 
              style={{ width: `${(currentStep?.payload?.step || 0) * 20}%` }}
            />
          </div>
          
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <CardTitle>Paso {currentStep?.payload?.progress || '1/5'}</CardTitle>
                <CardDescription>Responde a la siguiente pregunta del sistema</CardDescription>
              </div>
              <div className="text-xs font-mono bg-muted px-2 py-1 rounded">
                ID: {taskId?.substring(0,8)}
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {!currentStep ? (
              <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
                <Loader2 className="w-8 h-8 animate-spin mb-4 opacity-50" />
                <p>Esperando la siguiente pregunta del Flow...</p>
              </div>
            ) : (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
                <div className="bg-primary/5 border-l-4 border-primary p-6 rounded-r-lg">
                  <p className="text-lg font-medium leading-relaxed">
                    {currentStep.description}
                  </p>
                </div>

                <div className="space-y-4">
                  {currentStep?.payload?.fields ? (
                    // Renderizado DINÁMICO de campos (Paso 1)
                    currentStep.payload.fields.map((field: any) => (
                      <div key={field.id} className="space-y-2">
                        <label className="text-sm font-medium">{field.label}</label>
                        {field.type === 'textarea' ? (
                          <Textarea 
                            placeholder={field.placeholder}
                            value={formData[field.id] || ''}
                            onChange={(e) => setFormData(prev => ({ ...prev, [field.id]: e.target.value }))}
                            rows={4}
                          />
                        ) : (
                          <Input 
                            placeholder={field.placeholder}
                            value={formData[field.id] || ''}
                            onChange={(e) => setFormData(prev => ({ ...prev, [field.id]: e.target.value }))}
                          />
                        )}
                      </div>
                    ))
                  ) : (
                    // Renderizado TRADICIONAL (Pasos 2-5)
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Tu Respuesta / Definición</label>
                      <Textarea 
                        placeholder="Escribe aquí los detalles solicitados..."
                        rows={6}
                        value={answer}
                        onChange={(e) => setAnswer(e.target.value)}
                        className="resize-none"
                      />
                    </div>
                  )}
                </div>

                <Button 
                  onClick={sendAnswer} 
                  disabled={loading || (!answer.trim() && !currentStep?.payload?.fields)} 
                  className="w-full" 
                  size="lg"
                >
                  {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowRight className="mr-2 h-4 w-4" />}
                  Continuar al siguiente paso
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {status === 'completed' && (
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="flex flex-col items-center justify-center p-12 text-center">
            <div className="bg-green-500/10 p-4 rounded-full mb-4">
              <CheckCircle2 className="w-12 h-12 text-green-500" />
            </div>
            <CardTitle className="text-2xl mb-2">¡Construcción Completada!</CardTitle>
            <CardDescription className="mb-8">
              El agente ha sido registrado en el catálogo y está listo para ser orquestado.
            </CardDescription>
            <div className="flex gap-4">
              <Button variant="outline" onClick={() => location.reload()}>
                Crear otro Agente
              </Button>
              <Button asChild>
                <a href="/agents">Ver Catálogo de Agentes</a>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
