"use client"

import React, { useState, useCallback } from 'react'
import JSZip from 'jszip'
import { Upload, FileArchive, AlertCircle, Loader2 } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface BundleDropzoneProps {
  onFileSelect: (file: File, manifest: any) => void
  disabled?: boolean
}

export function BundleDropzone({ onFileSelect, disabled }: BundleDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const processFile = useCallback(async (file: File) => {
    if (!file.name.endsWith('.zip')) {
      setError('Solo se permiten archivos .zip')
      return
    }

    setIsProcessing(true)
    setError(null)

    try {
      const zip = new JSZip()
      const content = await zip.loadAsync(file)
      
      const manifestFile = content.file('manifest.json')
      if (!manifestFile) {
        setError('El bundle no contiene manifest.json en la raíz')
        return
      }

      const manifestText = await manifestFile.async('text')
      const manifest = JSON.parse(manifestText)
      
      onFileSelect(file, manifest)
    } catch (err) {
      setError('Error al procesar el archivo ZIP. Asegúrate de que no esté corrupto.')
      console.error(err)
    } finally {
      setIsProcessing(false)
    }
  }, [onFileSelect])

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    if (!disabled) setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (disabled) return

    const file = e.dataTransfer.files[0]
    if (file) processFile(file)
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) processFile(file)
  }

  return (
    <div className="space-y-4">
      <Card
        className={`relative border-2 border-dashed transition-colors ${
          isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && document.getElementById('bundle-upload')?.click()}
      >
        <input
          id="bundle-upload"
          type="file"
          className="hidden"
          accept=".zip"
          onChange={handleFileInput}
          disabled={disabled}
        />
        
        <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
          {isProcessing ? (
            <Loader2 className="h-12 w-12 text-muted-foreground animate-spin mb-4" />
          ) : (
            <Upload className={`h-12 w-12 mb-4 ${isDragging ? 'text-primary' : 'text-muted-foreground'}`} />
          )}
          
          <div className="space-y-1">
            <p className="text-lg font-medium">
              {isProcessing ? 'Procesando bundle...' : 'Arrastra tu bundle aquí'}
            </p>
            <p className="text-sm text-muted-foreground">
              O haz clic para seleccionar un archivo .zip (Máx. 50MB)
            </p>
          </div>
          
          <div className="mt-6 flex items-center gap-2 text-xs text-muted-foreground bg-muted px-3 py-1 rounded-full">
            <FileArchive className="h-3 w-3" />
            <span>FAP-Bundle v2.0 Standard</span>
          </div>
        </div>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error de validación local</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
