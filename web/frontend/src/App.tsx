import { Routes, Route } from 'react-router-dom'
import RoleSelect from './pages/RoleSelect'
import Chat from './pages/Chat'
import Knowledge from './pages/Knowledge'
import ErrorBoundary from './components/ErrorBoundary'

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<RoleSelect />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/knowledge" element={<Knowledge />} />
      </Routes>
    </ErrorBoundary>
  )
}
