import { Navigate, Outlet } from 'react-router-dom'

export default function PrivateRoute() {
  const token = localStorage.getItem('token')

  if (token) {
    try {
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const payload = JSON.parse(atob(base64))
      if (typeof payload.exp === 'number' && payload.exp > Date.now() / 1000) {
        return <Outlet />
      }
    } catch {
      // malformed token — fall through to redirect
    }
  }

  localStorage.removeItem('token')
  return <Navigate to="/login" replace />
}
