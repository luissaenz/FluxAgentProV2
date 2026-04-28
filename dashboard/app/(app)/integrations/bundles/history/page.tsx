import { Metadata } from 'next'
import { BundleTimeline } from '../components/BundleTimeline'
import { ArrowLeft, History, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Historial de Bundles | FluxAgentPro',
  description: 'Auditoría y control de versiones de bundles importados.',
}

export default function BundleHistoryPage() {
  return (
    <div className="container max-w-6xl py-10 space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/integrations/bundles">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Integraciones</span>
            <ChevronRight className="h-3 w-3" />
            <span className="font-medium text-foreground">Historial de Despliegues</span>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-primary/10 text-primary">
            <History className="h-6 w-6" />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-foreground to-foreground/50 bg-clip-text text-transparent">
            Historial de Bundles
          </h1>
        </div>
        <p className="text-xl text-muted-foreground max-w-2xl">
          Explora la cronología de importaciones, audita el código fuente de tus skills y gestiona el ciclo de vida de tus agentes.
        </p>
      </div>

      <div className="rounded-3xl border bg-card/30 backdrop-blur-sm p-8 shadow-2xl border-primary/5">
        <BundleTimeline />
      </div>
    </div>
  )
}
