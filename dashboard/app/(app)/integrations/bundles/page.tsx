"use client"

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Box, Loader2, Sparkles, CheckCircle2, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

import { BundleDropzone } from './components/BundleDropzone'
import { ValidationReport } from './components/ValidationReport'

export default function BundlesWizardPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [validationResult, setValidationResult] = useState<any>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)

  const handleFileSelect = async (selectedFile: File, _localManifest: any) => {
    setFile(selectedFile)
    setValidationResult(null)
    setIsValidating(true)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      // SUPUESTO: El org_id es manejado por el middleware de FastAPI/Supabase, 
      // pero en el cliente usamos los endpoints relativos configurados.
      const response = await fetch('/api/bundles/validate', {
        method: 'POST',
        body: formData,
      })

      const result = await response.json()
      setValidationResult(result)
      
      if (result.status === 'success') {
        toast.success('Validación completada con éxito')
      } else {
        toast.error('El bundle no pasó las validaciones de seguridad')
      }
    } catch (err) {
      setValidationResult({ 
        status: 'failed', 
        error: 'No se pudo contactar con el servicio de validación. Verifica tu conexión.' 
      })
      toast.error('Error de conexión')
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

      const response = await fetch('/api/bundles/import', {
        method: 'POST',
        body: formData,
      })

      const result = await response.json()
      
      if (response.ok && result.status === 'success') {
        setIsSuccess(true)
        toast.success('Bundle desplegado correctamente')
      } else {
        setValidationResult({ status: 'failed', error: result.detail || result.error })
        toast.error('Error crítico durante la persistencia')
      }
    } catch (err) {
      toast.error('Error de red durante la importación')
    } finally {
      setIsImporting(false)
    }
  }

  if (isSuccess) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 text-center animate-in fade-in zoom-in duration-500">
        <div className="h-24 w-24 bg-green-500/10 rounded-full flex items-center justify-center">
          <CheckCircle2 className="h-12 w-12 text-green-500" />
        </div>
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tighter">¡Bundle Desplegado!</h1>
          <p className="text-muted-foreground max-w-[500px]">
            Los agentes y skills han sido integrados en tu organización de forma atómica y segura.
          </p>
        </div>
        <div className="flex gap-4">
          <Button onClick={() => router.push('/agents')}>Ver Agentes</Button>
          <Button variant="outline" onClick={() => window.location.reload()}>Importar otro</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="container max-w-4xl py-10 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center justify-between">
        <Button variant="ghost" className="gap-2" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
          Volver
        </Button>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Integraciones</span>
          <ChevronRight className="h-3 w-3" />
          <span className="font-medium text-foreground">Bundle Wizard</span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <h1 className="text-4xl font-bold tracking-tight">Bundle Wizard</h1>
          <Sparkles className="h-6 w-6 text-yellow-500 fill-yellow-500" />
        </div>
        <p className="text-lg text-muted-foreground">
          Sube tus paquetes de agentes (ZIP) para validarlos y desplegarlos instantáneamente.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        <div className="lg:col-span-3 space-y-6">
          <section className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">1. Selección de Archivo</h2>
            <BundleDropzone 
              onFileSelect={handleFileSelect} 
              disabled={isValidating || isImporting} 
            />
          </section>

          {isValidating && (
            <div className="flex flex-col items-center justify-center p-12 space-y-4 border rounded-xl bg-muted/20 border-dashed">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm font-medium animate-pulse">Analizando seguridad y firmas digitales...</p>
            </div>
          )}

          {validationResult && (
            <section className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">2. Análisis de Integridad</h2>
              <ValidationReport report={validationResult} />
            </section>
          )}
        </div>

        <div className="lg:col-span-2">
          <aside className="sticky top-24 space-y-6 p-6 rounded-xl border bg-card text-card-foreground shadow-sm">
            <h3 className="font-bold flex items-center gap-2">
              <Box className="h-4 w-4" />
              Resumen de Acción
            </h3>
            
            <div className="space-y-4 text-sm">
              <div className="flex justify-between py-2 border-b">
                <span className="text-muted-foreground">Archivo:</span>
                <span className="font-medium truncate max-w-[150px]">{file?.name || 'Ninguno'}</span>
              </div>
              <div className="flex justify-between py-2 border-b">
                <span className="text-muted-foreground">Validación:</span>
                <span className={`font-medium ${
                  validationResult?.status === 'success' ? 'text-green-500' : 
                  validationResult?.status === 'failed' ? 'text-red-500' : 'text-muted-foreground'
                }`}>
                  {validationResult ? (validationResult.status === 'success' ? 'Aprobada' : 'Fallida') : 'Pendiente'}
                </span>
              </div>
            </div>

            <Button 
              className="w-full h-12 text-lg font-bold shadow-lg shadow-primary/20"
              disabled={!validationResult || validationResult.status !== 'success' || isImporting}
              onClick={handleImport}
            >
              {isImporting ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Importando...
                </>
              ) : (
                'Confirmar Despliegue'
              )}
            </Button>
            
            <p className="text-[10px] text-center text-muted-foreground">
              Al confirmar, los agentes se crearán o actualizarán de forma atómica en tu base de datos actual.
            </p>
          </aside>
        </div>
      </div>
    </div>
  )
}
