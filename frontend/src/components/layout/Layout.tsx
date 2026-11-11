import { Header } from './Header'

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="md:pl-64">{children}</div>
    </div>
  )
}

export default Layout
