import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { Overview } from './pages/Overview'
import { ActivityFeed } from './pages/ActivityFeed'
import { Analytics } from './pages/Analytics'
import { ConfigEditor } from './pages/ConfigEditor'
import { EscalationQueue } from './pages/EscalationQueue'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/activity" element={<ActivityFeed />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/config" element={<ConfigEditor />} />
        <Route path="/escalations" element={<EscalationQueue />} />
      </Route>
    </Routes>
  )
}
