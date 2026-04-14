'use client'

import { useState } from 'react'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Copy, Check, Server, Shield } from 'lucide-react'
import { toast } from 'sonner'

export default function MCPConfigPage() {
  const { orgId } = useCurrentOrg()
  const [copiedSse, setCopiedSse] = useState(false)
  
  // En producción esto vendría de una variable de entorno configurada en el despliegue
  const sseUrl = `${process.env.NEXT_PUBLIC_FASTAPI_URL || 'http://localhost:8000'}/api/v1/mcp/sse`

  const copyToClipboard = (text: string, setter: (v: boolean) => void) => {
    navigator.clipboard.writeText(text)
    setter(true)
    toast.success('Copiado al portapapeles')
    setTimeout(() => setter(false), 2000)
  }

  const claudeConfig = JSON.stringify({
    "mcpServers": {
      "flux-agent-pro": {
        "command": "python",
        "args": [
          "-m",
          "src.mcp.server",
          "--org-id",
          orgId
        ],
        "env": {
          "PYTHONPATH": "."
        }
      }
    }
  }, null, 2)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Configuración MCP</h2>
        <p className="text-muted-foreground">
          Conecta tus agentes con Claude Desktop y otras interfaces compatibles con Model Context Protocol.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-blue-200 bg-blue-50/30 dark:border-blue-900/30">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Server className="h-5 w-5 text-blue-600" />
              <CardTitle>Transporte SSE (Remoto)</CardTitle>
            </div>
            <CardDescription>
              Ideal para Claude Web, Mobile o clientes que no comparten sistema de archivos.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="sse-url">URL de Conexión</Label>
              <div className="flex gap-2">
                <Input
                  id="sse-url"
                  readOnly
                  value={sseUrl}
                  className="bg-white dark:bg-gray-950"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => copyToClipboard(sseUrl, setCopiedSse)}
                >
                  {copiedSse ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
            </div>
            <div className="rounded-md bg-white p-3 text-xs text-muted-foreground dark:bg-gray-950">
              <p className="font-semibold text-blue-700 dark:text-blue-400">Nota:</p>
              <p>Esta URL requiere incluir las cabeceras `Authorization` y `X-Org-ID` para autenticar la conexión de tu organización.</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-purple-600" />
              <CardTitle>Transporte Stdio (Local)</CardTitle>
            </div>
            <CardDescription>
              Configuración para Claude Desktop ejecutándose en esta misma máquina.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Configuración para `claude_desktop_config.json`</Label>
              <pre className="overflow-x-auto rounded-md bg-gray-900 p-4 text-[11px] text-gray-100">
                {claudeConfig}
              </pre>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
