import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import type { GuardConfig } from '../types'

export function ConfigEditor() {
  const [config, setConfig] = useState<GuardConfig | null>(null)
  const [yaml, setYaml] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  useEffect(() => {
    api.get<GuardConfig>('/api/config').then(data => {
      setConfig(data)
      setYaml(data.raw_yaml)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const save = async () => {
    setSaving(true)
    setStatus(null)
    try {
      const updated = await api.put<GuardConfig>('/api/config', { raw_yaml: yaml })
      setConfig(updated)
      setStatus({ type: 'success', msg: 'Config saved successfully' })
      setTimeout(() => setStatus(null), 3000)
    } catch (e) {
      setStatus({ type: 'error', msg: e instanceof Error ? e.message : 'Save failed' })
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Spinner />

  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h2 className="text-lg font-display font-bold text-slate-100 tracking-tight">Configuration</h2>
          <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-600 mt-1">Guard settings & validators</p>
        </div>
        <div className="flex items-center gap-3">
          {status && (
            <span className={`text-xs font-mono ${status.type === 'success' ? 'text-emerald-400' : 'text-rose-400'}`}>
              {status.msg}
            </span>
          )}
          <button
            onClick={save}
            disabled={saving}
            className="px-4 py-2 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded text-xs font-mono hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Config'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Structured View */}
        <div className="col-span-1 space-y-4">
          {/* Guard Settings */}
          <Card className="p-4 animate-fade-in-up opacity-0 delay-1">
            <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-3">Guard Settings</h3>
            <div className="space-y-2 text-xs font-mono">
              {config?.guard && Object.entries(config.guard).map(([key, val]) => (
                <div key={key} className="flex justify-between items-center">
                  <span className="text-slate-500">{key}</span>
                  <span className="text-slate-300">{String(val)}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Validators */}
          <Card className="p-4 animate-fade-in-up opacity-0 delay-2">
            <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-3">Validators ({config?.validators.length ?? 0})</h3>
            <div className="space-y-2">
              {(config?.validators ?? []).map((v, i) => (
                <div key={i} className="flex items-center gap-2 px-3 py-2 bg-slate-800/50 rounded border border-slate-700/30">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span className="text-xs font-mono text-slate-300 flex-1">{v.type}</span>
                  <span className="text-[10px] font-mono text-slate-600">
                    {Object.keys(v.settings).length} opts
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {/* Audit Config */}
          <Card className="p-4 animate-fade-in-up opacity-0 delay-3">
            <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500 mb-3">Audit</h3>
            <div className="space-y-2 text-xs font-mono">
              {config?.audit && Object.entries(config.audit).map(([key, val]) => (
                <div key={key} className="flex justify-between items-center">
                  <span className="text-slate-500">{key}</span>
                  <span className="text-slate-300">{String(val)}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* YAML Editor */}
        <Card className="col-span-2 flex flex-col animate-fade-in-up opacity-0 delay-2">
          <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
            <h3 className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500">YAML Editor</h3>
            <span className="text-[10px] font-mono text-slate-600">{yaml.split('\n').length} lines</span>
          </div>
          <textarea
            value={yaml}
            onChange={e => setYaml(e.target.value)}
            spellCheck={false}
            className="flex-1 min-h-[600px] p-4 bg-transparent text-xs font-mono text-slate-300 resize-none focus:outline-none leading-6 placeholder:text-slate-700"
            placeholder="# Paste your AgentGuard YAML config here..."
          />
        </Card>
      </div>
    </div>
  )
}
