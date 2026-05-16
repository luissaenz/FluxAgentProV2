'use client'

import { useQuery } from '@tanstack/react-query'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Puzzle, Terminal, Globe, ShieldCheck } from 'lucide-react'
import { CodeBlock } from '@/components/shared/CodeBlock'

export default function IntegrationsPage() {
  const { orgId } = useCurrentOrg()

  // 1. Consultar catálogo de servicios disponibles (TIPO C)
  const { data: availableServices, isLoading: loadingAvailable } = useQuery({
    queryKey: ['integrations-available', orgId],
    queryFn: () => api.get('/api/integrations/available'),
    enabled: !!orgId,
  })

  // 2. Consultar integraciones activas
  const { data: activeIntegrations, isLoading: loadingActive } = useQuery({
    queryKey: ['integrations-active', orgId],
    queryFn: () => api.get('/api/integrations/active'),
    enabled: !!orgId,
  })

  const mcpConfig = {
    stdio: {
      command: 'python -m src.mcp.server',
      args: [`--org-id ${orgId || 'TU-ORG-ID'}`],
    },
    sse: {
      url: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/mcp/sse?org_id=${orgId || 'TU-ORG-ID'}`,
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Integraciones y MCP</h2>
        <p className="text-muted-foreground">
          Conectá FluxAgentPro con agentes externos o extendé sus capacidades con el catálogo de servicios.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* MCP Connection Info */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Terminal className="h-5 w-5 text-primary" />
              Conexión MCP (Claude Desktop)
            </CardTitle>
            <CardDescription>
              Configurá tu cliente MCP para operar este workspace directamente.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium text-white">Configuración Stdio (Local)</p>
              <CodeBlock 
                code={{
                  mcpServers: {
                    "flux-agent-pro": {
                      command: "python",
                      args: ["-m", "src.mcp.server", "--org-id", orgId || "TU-ORG-ID"],
                      env: { "PYTHONPATH": "." }
                    }
                  }
                }} 
              />
            </div>
            
            <div className="space-y-2">
              <p className="text-sm font-medium text-white">Endpoint SSE (Remoto)</p>
              <div className="flex items-center gap-2 rounded-md border bg-muted p-2 text-xs font-mono text-white overflow-x-auto">
                <Globe className="h-4 w-4 shrink-0 text-muted-foreground" />
                {mcpConfig.sse.url}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Status & Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <ShieldCheck className="h-5 w-5 text-green-500" />
              Estado del Servidor MCP
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between py-2 border-b border-white/10">
              <span className="text-sm text-muted-foreground">Transporte SSE</span>
              <Badge variant="success">Online</Badge>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-white/10">
              <span className="text-sm text-muted-foreground">Flow-to-Tool Adapter</span>
              <Badge variant="success">Activo</Badge>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-muted-foreground">Aislamiento Org</span>
              <Badge variant="outline" className="text-white border-white/20">Habilitado ({orgId?.slice(0,8)}...)</Badge>
            </div>
            <Button variant="outline" className="w-full text-white border-white/20 hover:bg-white/5" disabled>
              Ver Logs en tiempo real
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Service Catalog */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <Puzzle className="h-5 w-5 text-primary" />
            Catálogo de Servicios (TIPO C)
          </h3>
          <Badge variant="secondary" className="text-white bg-white/10">
            {availableServices?.services?.length || 0} disponibles
          </Badge>
        </div>

        {loadingAvailable ? (
          <LoadingSpinner label="Cargando catálogo..." />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {availableServices?.services?.map((service: any) => {
              const isActive = activeIntegrations?.integrations?.some((a: any) => a.service_id === service.id)
              return (
                <Card key={service.id} className="transition-all hover:border-primary/50">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base text-white">{service.name}</CardTitle>
                      {isActive ? (
                        <Badge variant="success">Activo</Badge>
                      ) : (
                        <Badge variant="outline" className="text-white border-white/20">Disponible</Badge>
                      )}
                    </div>
                    <CardDescription className="line-clamp-2">{service.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="font-semibold text-white">Provider:</span> {service.provider_name}
                      </div>
                      <Button variant="secondary" size="sm" className="mt-2 w-full text-white bg-white/5 hover:bg-white/10" disabled={!isActive}>
                        {isActive ? 'Configurar' : 'Activar Integración'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
