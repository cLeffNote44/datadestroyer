import { useUIStore } from '../../stores/uiStore'
import Header from './Header'
import Sidebar from './Sidebar'
import Notifications from '../common/Notifications'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const sidebarOpen = useUIStore((state) => state.sidebarOpen)

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <Sidebar />

      {/* Main content */}
      <div
        className={`transition-all duration-300 ${
          sidebarOpen ? 'lg:ml-64' : 'lg:ml-0'
        } pt-16`}
      >
        <main className="p-6">{children}</main>
      </div>

      {/* Notifications */}
      <Notifications />
    </div>
  )
}
