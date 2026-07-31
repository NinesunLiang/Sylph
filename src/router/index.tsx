import { lazy } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { PATHS } from './paths'

// Lazy-loaded pages
const AppLayout = lazy(() => import('@/layouts/AppLayout'))
const ConsolePage = lazy(() => import('@/pages/console'))
const DiscoverPage = lazy(() => import('@/pages/discover'))
const EcosystemPage = lazy(() => import('@/pages/ecosystem'))
const LoginPage = lazy(() => import('@/pages/login'))
const ReportsPage = lazy(() => import('@/pages/reports'))
const NotFoundPage = lazy(() => import('@/pages/not-found'))
const AuthCallbackPage = lazy(() => import('@/pages/auth-callback'))

export const router = createBrowserRouter([
  {
    path: PATHS.CONSOLE,
    element: <AppLayout />,
    children: [
      { index: true, element: <ConsolePage /> },
      { path: '/chat', element: <ConsolePage /> },
      { path: PATHS.DISCOVER, element: <DiscoverPage /> },
      { path: PATHS.ECOSYSTEM, element: <EcosystemPage /> },
      { path: PATHS.LOGIN, element: <LoginPage /> },
      { path: PATHS.REPORTS, element: <ReportsPage /> },
      { path: PATHS.AUTH_CALLBACK, element: <AuthCallbackPage /> },
      { path: '404', element: <NotFoundPage /> },
      { path: '*', element: <Navigate to="/404" replace /> },
    ],
  },
])
