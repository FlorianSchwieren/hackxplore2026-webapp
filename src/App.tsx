import { Suspense, lazy } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MapProvider } from '@/context/MapContext'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import { PageLoader } from '@/components/common/LoadingSpinner'
import MainPage from '@/pages/MainPage'

const StatsPage = lazy(() => import('@/pages/StatsPage'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <MapProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<MainPage />} />
              <Route
                path="/stats"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <StatsPage />
                  </Suspense>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </MapProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
