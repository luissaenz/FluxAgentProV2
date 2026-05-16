import { Skeleton } from '@/components/ui/skeleton'

export default function Loading() {
  return (
    <div className="flex h-full flex-col space-y-4">
      <div className="flex items-center justify-between px-1 py-2">
        <Skeleton className="h-8 w-48" />
        <div className="flex items-center gap-2">
          <Skeleton className="h-9 w-28" />
          <Skeleton className="h-9 w-28" />
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <div className="grid h-full gap-4 lg:grid-cols-[60%_40%]">
          <Skeleton className="h-full w-full rounded-lg" />
          <div className="flex flex-col overflow-hidden rounded-lg border bg-card p-4">
            <div className="mb-3 h-5 w-40 rounded" />
            <div className="flex flex-col gap-3">
              <Skeleton className="h-10 w-full rounded-md" />
              <Skeleton className="h-10 w-full rounded-md" />
              <Skeleton className="h-24 w-full rounded-md" />
              <Skeleton className="h-20 w-full rounded-md" />
              <Skeleton className="h-10 w-full rounded-md" />
              <div className="flex gap-2 pt-2">
                <Skeleton className="h-9 flex-1 rounded-md" />
                <Skeleton className="h-9 flex-1 rounded-md" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
