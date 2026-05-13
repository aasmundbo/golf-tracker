import { useState, useEffect } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import api from '../api/client'

export default function AdminRoute() {
  const [state, setState] = useState('loading')

  useEffect(() => {
    api.get('/users/me')
      .then(res => setState(res.data.role === 'admin' ? 'admin' : 'denied'))
      .catch(() => setState('denied'))
  }, [])

  if (state === 'loading') return null
  if (state === 'denied') return <Navigate to="/" replace />
  return <Outlet />
}
