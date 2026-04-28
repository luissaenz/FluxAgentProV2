'use client'

import { useState, useEffect } from 'react'
import { ColumnDef } from '@tanstack/react-table'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { 
  History, 
  Trash2, 
  Eye, 
  CheckCircle2, 
  XCircle, 
  Clock,
  MoreHorizontal
} from 'lucide-react'
import { DataTable } from '@/components/data-table'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogDescription
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface BundleImport {
  id: string
  bundle_name: string
  version: string
  status: string
  imported_at: string
  is_active: boolean
}

interface BundleDetails {
  bundle_id: string
  agents: string[]
  flows: string[]
  skills: { name: string; code: string }[]
}

export function BundleTimeline() {
  const [data, setData] = useState<BundleImport[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedBundle, setSelectedBundle] = useState<BundleDetails | null>(null)
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)
  const [isDetailsLoading, setIsDetailsLoading] = useState(false)

  const fetchHistory = async () => {
    try {
      setIsLoading(true)
      const history = await api.get('/api/bundles/history')
      // Filtrar por activos según Criterio de Aceptación (o mostrar todos con badge de borrado)
      // Análisis dice: "El filtrado se hará inicialmente client-side sobre los últimos 50 registros"
      setData(history.slice(0, 50))
    } catch (error: any) {
      toast.error('Error al cargar el historial: ' + error.message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  const handleShowDetails = async (bundleId: string) => {
    try {
      setIsDetailsLoading(true)
      setIsDetailsOpen(true)
      const details = await api.get(`/api/bundles/${bundleId}/details`)
      setSelectedBundle(details)
    } catch (error: any) {
      toast.error('Error al cargar detalles: ' + error.message)
      setIsDetailsOpen(false)
    } finally {
      setIsDetailsLoading(false)
    }
  }

  const handleDelete = async (bundleId: string) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este bundle? Esto desactivará todos sus componentes.')) {
      return
    }

    try {
      await api.delete(`/api/bundles/${bundleId}`)
      toast.success('Bundle eliminado correctamente')
      fetchHistory()
    } catch (error: any) {
      toast.error('Error al eliminar bundle: ' + error.message)
    }
  }

  const columns: ColumnDef<BundleImport>[] = [
    {
      accessorKey: 'bundle_name',
      header: 'Nombre del Bundle',
      cell: ({ row }) => (
        <div className="font-medium">{row.getValue('bundle_name')}</div>
      )
    },
    {
      accessorKey: 'version',
      header: 'Versión',
      cell: ({ row }) => (
        <Badge variant="outline">{row.getValue('version')}</Badge>
      )
    },
    {
      accessorKey: 'status',
      header: 'Estado',
      cell: ({ row }) => {
        const status = row.getValue('status') as string
        const isActive = row.original.is_active

        if (!isActive) {
          return <Badge variant="secondary">Eliminado</Badge>
        }

        switch (status) {
          case 'committed':
            return (
              <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
                <CheckCircle2 className="mr-1 h-3 w-3" /> Activo
              </Badge>
            )
          case 'failed':
            return (
              <Badge variant="destructive">
                <XCircle className="mr-1 h-3 w-3" /> Fallido
              </Badge>
            )
          default:
            return (
              <Badge variant="outline" className="animate-pulse">
                <Clock className="mr-1 h-3 w-3" /> {status}
              </Badge>
            )
        }
      }
    },
    {
      accessorKey: 'imported_at',
      header: 'Fecha de Importación',
      cell: ({ row }) => {
        const date = new Date(row.getValue('imported_at'))
        return (
          <div className="text-muted-foreground text-sm">
            {format(date, "d 'de' MMMM, HH:mm", { locale: es })}
          </div>
        )
      }
    },
    {
      id: 'actions',
      cell: ({ row }) => {
        const bundle = row.original

        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => handleShowDetails(bundle.id)}>
                <Eye className="mr-2 h-4 w-4" /> Ver Detalles
              </DropdownMenuItem>
              {bundle.is_active && (
                <DropdownMenuItem 
                  className="text-destructive focus:text-destructive"
                  onClick={() => handleDelete(bundle.id)}
                >
                  <Trash2 className="mr-2 h-4 w-4" /> Eliminar
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )
      }
    }
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Historial de Despliegues</h2>
          <p className="text-muted-foreground">
            Auditoría de todos los bundles importados en la organización.
          </p>
        </div>
        <Button variant="outline" onClick={fetchHistory} disabled={isLoading}>
          <Clock className="mr-2 h-4 w-4" /> Actualizar
        </Button>
      </div>

      <DataTable 
        columns={columns} 
        data={data} 
        isLoading={isLoading} 
        emptyMessage="No hay registros de importación todavía."
      />

      <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Detalles del Bundle</DialogTitle>
            <DialogDescription>
              Contenido importado y auditoría de código fuente.
            </DialogDescription>
          </DialogHeader>

          {isDetailsLoading ? (
            <div className="flex items-center justify-center h-64">
              <Clock className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : selectedBundle ? (
            <Tabs defaultValue="agents" className="flex-1 flex flex-col overflow-hidden">
              <TabsList>
                <TabsTrigger value="agents">Agentes ({selectedBundle.agents.length})</TabsTrigger>
                <TabsTrigger value="flows">Flujos ({selectedBundle.flows.length})</TabsTrigger>
                <TabsTrigger value="skills">Skills ({selectedBundle.skills.length})</TabsTrigger>
              </TabsList>
              
              <TabsContent value="agents" className="flex-1 overflow-auto mt-4">
                <div className="grid grid-cols-2 gap-2">
                  {selectedBundle.agents.map((agent, i) => (
                    <div key={i} className="p-3 border rounded-md bg-muted/50">
                      <span className="font-medium">{agent}</span>
                    </div>
                  ))}
                  {selectedBundle.agents.length === 0 && (
                    <p className="text-muted-foreground italic">No hay agentes en este bundle.</p>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="flows" className="flex-1 overflow-auto mt-4">
                <div className="grid grid-cols-2 gap-2">
                  {selectedBundle.flows.map((flow, i) => (
                    <div key={i} className="p-3 border rounded-md bg-muted/50">
                      <span className="font-medium">{flow}</span>
                    </div>
                  ))}
                  {selectedBundle.flows.length === 0 && (
                    <p className="text-muted-foreground italic">No hay flujos en este bundle.</p>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="skills" className="flex-1 overflow-hidden mt-6 flex flex-col gap-4">
                <div className="flex-1 overflow-hidden flex gap-6">
                  <div className="w-[280px] overflow-auto border rounded-xl bg-muted/30 p-2">
                    <p className="text-[10px] font-bold uppercase text-muted-foreground px-3 mb-2 tracking-widest">
                      Archivos de Skill
                    </p>
                    <div className="space-y-1">
                      {selectedBundle.skills.map((skill, i) => (
                        <button
                          key={i}
                          className="w-full text-left p-3 hover:bg-background rounded-lg border border-transparent hover:border-border transition-all group flex items-center gap-2"
                          onClick={() => {
                            const el = document.getElementById(`skill-code-${i}`)
                            el?.scrollIntoView({ behavior: 'smooth' })
                          }}
                        >
                          <div className="h-2 w-2 rounded-full bg-purple-500" />
                          <span className="font-mono text-xs truncate group-hover:text-primary transition-colors">
                            {skill.name}.py
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex-1 overflow-hidden border rounded-xl bg-[#0d0d0d] shadow-2xl relative">
                    <div className="absolute top-0 left-0 right-0 h-10 bg-zinc-900/50 border-b border-zinc-800 flex items-center px-4 justify-between z-10 backdrop-blur-md">
                      <div className="flex gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full bg-red-500/20 border border-red-500/40" />
                        <div className="w-2.5 h-2.5 rounded-full bg-amber-500/20 border border-amber-500/40" />
                        <div className="w-2.5 h-2.5 rounded-full bg-green-500/20 border border-green-500/40" />
                      </div>
                      <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">
                        Modo Auditoría: Solo Lectura
                      </span>
                    </div>
                    
                    <ScrollArea className="h-full pt-10">
                      <div className="p-6">
                        {selectedBundle.skills.map((skill, i) => (
                          <div key={i} id={`skill-code-${i}`} className="mb-12 last:mb-0">
                            <div className="flex items-center gap-3 mb-4 group">
                              <div className="h-px flex-1 bg-zinc-800" />
                              <h4 className="text-zinc-500 text-[10px] font-mono uppercase tracking-tighter">
                                {skill.name}.py
                              </h4>
                              <div className="h-px flex-1 bg-zinc-800" />
                            </div>
                            <div className="relative rounded-lg overflow-hidden group">
                              <div className="absolute left-0 top-0 bottom-0 w-12 bg-zinc-900/30 border-r border-zinc-800/50 flex flex-col items-center pt-4 select-none">
                                {skill.code.split('\n').map((_, lineIdx) => (
                                  <span key={lineIdx} className="text-[10px] text-zinc-700 font-mono leading-6 h-6">
                                    {lineIdx + 1}
                                  </span>
                                ))}
                              </div>
                              <pre className="pl-16 pr-4 py-4 text-zinc-300 font-mono text-sm leading-6 overflow-x-auto selection:bg-purple-500/30">
                                <code>{skill.code}</code>
                              </pre>
                            </div>
                          </div>
                        ))}
                        {selectedBundle.skills.length === 0 && (
                          <div className="flex flex-col items-center justify-center h-64 text-zinc-600 space-y-4">
                            <Eye className="h-12 w-12 opacity-20" />
                            <p className="text-sm font-medium italic">No se detectó código fuente de skills.</p>
                          </div>
                        )}
                      </div>
                    </ScrollArea>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
