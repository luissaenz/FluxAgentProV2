'use client'

import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

interface BackButtonProps {
  href: string
  label?: string
}

export function BackButton({ href, label = 'Volver' }: BackButtonProps) {
  return (
    <Button variant="ghost" size="sm" asChild className="mb-4">
      <Link href={href}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        {label}
      </Link>
    </Button>
  )
}
