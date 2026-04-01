export function Spinner() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="relative">
        <div className="w-8 h-8 border-2 border-slate-700 rounded-full" />
        <div className="absolute top-0 left-0 w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
      <span className="ml-3 text-xs font-mono text-slate-500 uppercase tracking-wider">Loading...</span>
    </div>
  )
}
