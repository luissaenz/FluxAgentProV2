"use client"

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Box, Loader2, Sparkles, CheckCircle2, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

import { BundleDropzone } from './components/BundleDropzone'
import { ValidationReport } from './components/ValidationReport'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Box, Loader2, Sparkles, CheckCircle2, ChevronRight, AlertCircle, History } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { api } from '@/lib/api'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

import { BundleDropzone } from './components/BundleDropzone'
import { ValidationReport } from './components/ValidationReport'

export default function BundlesWizardPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [validationResult, setValidationResult] = useState<any>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [allowDowngrade, setAllowDowngrade] = useState(false)
  const [isVersionConflict, setIsVersionConflict] = useState(false)

  const handleFileSelect = async (selectedFile: File, _localManifest: any) => {
    setFile(selectedFile)
    setValidationResult(null)
    setIsVersionConflict(false)
    setAllowDowngrade(false)
    setIsValidating(true)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const result = await api.post('/api/bundles/validate', formData)
      setValidationResult(result)
      
      if (result.status === 'success') {
        toast.success('Validación completada con éxito')
      } else {
        toast.error('El bundle no pasó las validaciones de seguridad')
      }
    } catch (err: any) {
      setValidationResult({ 
        status: 'failed', 
        error: err.message || 'No se pudo contactar con el servicio de validación.' 
      })
      toast.error('Error de validación')
    } finally {
      setIsValidating(false)
    }
  }

  const handleImport = async () => {
    if (!file) return
    setIsImporting(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      // El endpoint /import recibe 'force' como query param según bundles.py
      const result = await api.post(`/api/bundles/import${allowDowngrade ? '?force=true' : ''}`, formData)
      
      if (result.status === 'success') {
        setIsSuccess(true)
        toast.success('Bundle desplegado correctamente')
      } else {
        setValidationResult({ status: 'failed', error: result.detail || result.error })
        toast.error('Error crítico durante la persistencia')
      }
    } catch (err: any) {
      const message = err.message || ''
      if (message.includes('lower than current') || message.includes('version')) {
        setIsVersionConflict(true)
        toast.warning('Conflicto de versión detectado')
      } else {
        toast.error('Error de importación: ' + message)
      }
      
      setValidationResult({ 
        status: 'failed', 
        error: message 
      })
    } finally {
      setIsImporting(false)
    }
  }

  if (isSuccess) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 text-center animate-in fade-in zoom-in duration-500">
        <div className="h-24 w-24 bg-green-500/10 rounded-full flex items-center justify-center border border-green-500/20">
          <CheckCircle2 className="h-12 w-12 text-green-500" />
        </div>
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tighter">¡Bundle Desplegado!</h1>
          <p className="text-muted-foreground max-w-[500px] text-lg">
            Los agentes y skills han sido integrados en tu organización de forma atómica y segura.
          </p>
        </div>
        <div className="flex gap-4">
          <Button size="lg" onClick={() => router.push('/agents')}>Ver Agentes</Button>
          <Button size="lg" variant="outline" onClick={() => router.push('/integrations/bundles/history')}>Ver Historial</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="container max-w-5xl py-10 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Integraciones</span>
            <ChevronRight className="h-3 w-3" />
            <span className="font-medium text-foreground">Bundle Wizard</span>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => router.push('/integrations/bundles/history')}>
          <History className="mr-2 h-4 w-4" /> Historial
        </Button>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-foreground to-foreground/50 bg-clip-text text-transparent">
            Bundle Wizard
          </h1>
          <Sparkles className="h-6 w-6 text-yellow-500 fill-yellow-500" />
        </div>
        <p className="text-xl text-muted-foreground">
          Sube tus paquetes de agentes (ZIP) para validarlos y desplegarlos instantáneamente.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-8">
          <section className="space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80 flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-[10px]">1</span>
              Selección de Archivo
            </h2>
            <BundleDropzone 
              onFileSelect={handleFileSelect} 
              disabled={isValidating || isImporting} 
            />
          </section>

          {isValidating && (
            <div className="flex flex-col items-center justify-center p-16 space-y-4 border rounded-2xl bg-muted/30 border-dashed animate-pulse">
              <div className="relative">
                <Loader2 className="h-10 w-10 animate-spin text-primary" />
                <div className="absolute inset-0 blur-xl bg-primary/20 animate-pulse" />
              </div>
              <p className="text-sm font-semibold tracking-wide uppercase text-muted-foreground">Analizando seguridad y firmas digitales...</p>
            </div>
          )}

          {validationResult && (
            <section className="space-y-4 animate-in fade-in slide-in-from-top-4 duration-500">
              <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-[10px]">2</span>
                Resultado del Análisis
              </h2>
              <ValidationReport report={validationResult} />
            </section>
          )}
        </div>

        <div className="lg:col-span-4">
          <aside className="sticky top-24 space-y-6 p-8 rounded-2xl border bg-card/50 backdrop-blur-sm text-card-foreground shadow-xl border-primary/10">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <Box className="h-5 w-5 text-primary" />
              Resumen de Acción
            </h3>
            
            <div className="space-y-4 text-sm">
              <div className="flex justify-between py-3 border-b border-muted/50">
                <span className="text-muted-foreground">Archivo:</span>
                <span className="font-semibold truncate max-w-[180px]">{file?.name || 'Ninguno'}</span>
              </div>
              <div className="flex justify-between py-3 border-b border-muted/50">
                <span className="text-muted-foreground">Validación:</span>
                <span className={`font-bold ${
                  validationResult?.status === 'success' ? 'text-green-500' : 
                  validationResult?.status === 'failed' ? 'text-red-500' : 'text-muted-foreground'
                }`}>
                  {validationResult ? (validationResult.status === 'success' ? 'APROBADA' : 'FALLIDA') : 'PENDIENTE'}
                </span>
              </div>
            </div>

            {isVersionConflict && (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-3 animate-in shake-2 duration-300">
                <div className="flex items-start gap-2 text-amber-600">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                  <p className="text-xs font-medium">
                    La versión del bundle es inferior a la actual. Esto causará un rollback.
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="downgrade" 
                    checked={allowDowngrade} 
                    onCheckedChange={(checked) => setAllowDowngrade(checked as boolean)}
                  />
                  <Label htmlFor="downgrade" className="text-xs font-bold cursor-pointer">
                    Permitir Downgrade (Force)
                  </Label>
                </div>
              </div>
            )}

            <Button 
              size="lg"
              className="w-full h-14 text-lg font-extrabold shadow-2xl shadow-primary/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
              disabled={!validationResult || (validationResult.status !== 'success' && !isVersionConflict) || isImporting || (isVersionConflict && !allowDowngrade)}
              onClick={handleImport}
            >
              {isImporting ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  PERSISTIENDO...
                </>
              ) : (
                'DESPLEGAR BUNDLE'
              )}
            </Button>
            
            <p className="text-[10px] text-center text-muted-foreground font-medium leading-relaxed">
              Al confirmar, los agentes se crearán o actualizarán de forma atómica en tu organización. Esta acción es irreversible sin un nuevo despliegue.
            </p>
          </aside>
        </div>
      </div>
    </div>
  )
}
