"use client"

import React from 'react'
import { CheckCircle2, AlertTriangle, ShieldCheck, Box, UserCheck, Code, Workflow } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface ValidationReportProps {
  report: {
    status: string
    bundle_info?: {
      name: string
      version: string
      description?: string
    }
    agents_count: number
    flows_count: number
    skills_count: number
    security_report?: any
    error?: string
  }
}

export function ValidationReport({ report }: ValidationReportProps) {
  const isSuccess = report.status === 'success'

  return (
    <Card className={`overflow-hidden border-2 ${
      isSuccess ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5'
    }`}>
      <CardHeader className="border-b bg-muted/30 py-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            {isSuccess ? (
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-red-500" />
            )}
            Reporte de Validación Remota
          </CardTitle>
          <Badge className={isSuccess ? 'bg-green-500/20 text-green-600 hover:bg-green-500/30' : ''} variant={isSuccess ? 'outline' : 'destructive'}>
            {isSuccess ? 'Listo para importar' : 'Error crítico'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-6 space-y-6">
        {report.error && (
          <div className="p-4 rounded-md bg-red-500/10 text-red-500 text-sm font-mono border border-red-500/20 break-words">
            <p className="font-bold mb-1">DETALLE DEL ERROR:</p>
            {report.error}
          </div>
        )}

        {isSuccess && report.bundle_info && (
          <div className="space-y-6">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <h3 className="text-xl font-bold tracking-tight">{report.bundle_info.name}</h3>
                <p className="text-sm text-muted-foreground">{report.bundle_info.description || 'Sin descripción'}</p>
              </div>
              <Badge variant="secondary">v{report.bundle_info.version}</Badge>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="p-3 rounded-lg bg-background border flex flex-col items-center gap-2">
                <UserCheck className="h-5 w-5 text-blue-500" />
                <span className="text-lg font-bold">{report.agents_count}</span>
                <span className="text-[10px] uppercase font-semibold text-muted-foreground">Agentes</span>
              </div>
              <div className="p-3 rounded-lg bg-background border flex flex-col items-center gap-2">
                <Workflow className="h-5 w-5 text-orange-500" />
                <span className="text-lg font-bold">{report.flows_count}</span>
                <span className="text-[10px] uppercase font-semibold text-muted-foreground">Workflows</span>
              </div>
              <div className="p-3 rounded-lg bg-background border flex flex-col items-center gap-2">
                <Code className="h-5 w-5 text-purple-500" />
                <span className="text-lg font-bold">{report.skills_count}</span>
                <span className="text-[10px] uppercase font-semibold text-muted-foreground">Skills</span>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-background/50 border-2 border-dashed space-y-3">
              <p className="text-xs font-bold uppercase text-muted-foreground flex items-center gap-2">
                <ShieldCheck className="h-3 w-3 text-green-500" />
                Análisis de Seguridad (Sandbox)
              </p>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Escaneo de AST (Sintaxis segura)</span>
                  {report.security_report?.ast_scanned ? (
                    <span className="text-green-500 font-bold uppercase flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" /> PASSED
                    </span>
                  ) : (
                    <span className="text-amber-500 font-bold uppercase">SKIPPED</span>
                  )}
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Compilación RestrictedPython</span>
                  {report.security_report?.restricted_python_verified ? (
                    <span className="text-green-500 font-bold uppercase flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" /> VERIFIED
                    </span>
                  ) : (
                    <span className="text-red-500 font-bold uppercase flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" /> FAILED
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
