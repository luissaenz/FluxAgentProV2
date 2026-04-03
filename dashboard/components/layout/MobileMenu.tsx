'use client'

import React, { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Menu, X } from 'lucide-react'
import { Sidebar } from './Sidebar'

interface MobileMenuProps {
  pendingApprovals?: number
}

export function MobileMenu({ pendingApprovals = 0 }: MobileMenuProps) {
  const [open, setOpen] = useState(false)

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          className="rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100 md:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-6 w-6" />
        </button>
      </Dialog.Trigger>
      
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm transition-opacity data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        
        <Dialog.Content className="fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-xl transition-transform data-[state=closed]:-translate-x-full data-[state=open]:translate-x-0 data-[state=open]:animate-in data-[state=closed]:animate-out dark:bg-gray-900">
          <div className="h-full">
            <Sidebar 
              pendingApprovals={pendingApprovals} 
              onClose={() => setOpen(false)} 
            />
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
