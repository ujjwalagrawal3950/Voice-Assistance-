import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Moon, Sun, User, LayoutDashboard, ShoppingCart, Bot, SlidersHorizontal } from 'lucide-react'
import { api } from '@/api/client'
import type { Seller } from '@/types'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/', label: 'Overview', icon: LayoutDashboard },
  { href: '/skus', label: 'Products', icon: ShoppingCart },
  { href: '/kam', label: 'Virtual KAM', icon: Bot },
  { href: '/settings', label: 'Settings', icon: SlidersHorizontal },
]

export function Header() {
  const location = useLocation()
  const [seller, setSeller] = useState<Seller | null>(null)
  const [loading, setLoading] = useState(true)
  const [dark, setDark] = useState(false)

  useEffect(() => {
    api.getSellerProfile()
      .then((s) => { setSeller(s); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    const root = window.document.documentElement
    if (dark) root.classList.add('dark')
    else root.classList.remove('dark')
  }, [dark])

  if (loading) return null

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur supports-[backdrop-blur]:bg-background/60">
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold">
              V
            </div>
            <span className="font-semibold tracking-tight text-sm">Virtual KAM</span>
          </div>
          <div className="hidden md:flex items-center gap-1 border-l border-border pl-4">
            <User size={16} strokeWidth={2} className="text-muted-foreground" />
            <span className="text-sm font-medium text-muted-foreground truncate max-w-xs">
              {seller?.display_name || 'Seller'}
            </span>
          </div>
          <nav className="hidden md:flex items-center gap-6 px-6 py-1 border-l border-border ml-4 text-xs font-medium">
            {navItems.map((item) => {
              const Icon = item.icon
              const active = location.pathname === item.href
              return (
                <a
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-1.5 px-2 py-1.5 rounded-md transition-colors',
                    active
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  <Icon size={15} strokeWidth={2} />
                  {item.label}
                </a>
              )
            })}
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="p-2 text-muted-foreground hover:bg-accent rounded-md"
            onClick={() => setDark((d) => !d)}
            aria-label={dark ? 'Light mode' : 'Dark mode'}
          >
            {dark ? <Sun size={17} strokeWidth={2} /> : <Moon size={17} strokeWidth={2} />}
          </button>
        </div>
      </div>
    </header>
  )
}
