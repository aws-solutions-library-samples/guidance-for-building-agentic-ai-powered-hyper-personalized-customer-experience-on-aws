import { Moon, Sun, Search, Heart, ShoppingCart } from 'lucide-react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { Badge } from './ui/badge'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { setSearchCategory, toggleDarkMode } from '../store/slices/uiSlice'
import { useNavigate } from 'react-router-dom'
import logo from '../assets/sample-logo-3.png'
import CustomerDropdown from './CustomerDropdown'

interface NavbarProps {
  searchQuery?: string
  onSearchQueryChange?: (query: string) => void
  onSearch?: () => void
  onKeyPress?: (e: React.KeyboardEvent) => void
  showBackButton?: boolean
  onBackClick?: () => void
  onLogoClick?: () => void
  showSearch?: boolean
  disableSearch?: boolean
  rightContent?: React.ReactNode
}

const Navbar: React.FC<NavbarProps> = ({
  searchQuery = '',
  onSearchQueryChange,
  onSearch,
  onKeyPress,
  showBackButton = false,
  onBackClick,
  onLogoClick,
  showSearch = true,
  disableSearch = false,
  rightContent
}) => {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const { searchCategory, darkMode } = useAppSelector((state) => state.ui)
  
  const categories = ['Basic', 'Semantic']

  const handleCategoryChange = (newCategory: string) => {
    dispatch(setSearchCategory(newCategory as 'Basic' | 'Semantic'))
  }

  const handleToggleDarkMode = () => {
    dispatch(toggleDarkMode())
    
    if (!darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  return (
    <header className="sticky top-0 z-40 bg-background/80 backdrop-blur-md border-b border-border/50">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo and Brand */}
          <div className="flex items-center gap-3">
            {showBackButton && onBackClick && (
              <Button variant="ghost" size="icon" onClick={onBackClick} className="hover:bg-accent hover:text-accent-foreground">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </Button>
            )}
            <div 
              className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity"
              onClick={() => {
                if (onLogoClick) {
                  onLogoClick()
                } else {
                  navigate('/')
                }
              }}
            >
              <img src={logo} className="w-10 h-10 rounded-xl" alt="Medicine Mart" />
              <div>
                <h1 className="text-lg font-semibold tracking-tight">MedicineMart</h1>
                <p className="text-xs text-muted-foreground leading-none">Healthcare & Wellness</p>
              </div>
            </div>
          </div>

          {/* Search Bar */}
          {showSearch && (
            <div className="flex-1 max-w-2xl mx-8">
              <div className={`flex items-center rounded-xl overflow-hidden border border-border/50 ${disableSearch ? 'bg-muted/10 opacity-60' : 'bg-muted/30'}`}>
                <Select 
                  value={searchCategory} 
                  onValueChange={disableSearch ? undefined : handleCategoryChange}
                  disabled={disableSearch}
                >
                  <SelectTrigger className="w-32 h-10 border-0 bg-transparent text-xs focus:ring-0 rounded-none">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat} value={cat} className="text-xs">
                        {cat}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="w-px h-6 bg-border/50" />
                <Input
                  type="text"
                  placeholder="Search products, brands, or categories..."
                  value={searchQuery}
                  onChange={disableSearch ? undefined : (e) => onSearchQueryChange?.(e.target.value)}
                  onKeyDown={disableSearch ? undefined : onKeyPress}
                  disabled={disableSearch}
                  className="flex-1 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 h-10 rounded-none"
                />
                <Button
                  onClick={disableSearch ? undefined : onSearch}
                  size="sm"
                  disabled={disableSearch}
                  className="h-8 px-4 m-1 rounded-lg"
                >
                  <Search className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Header Actions */}
          {rightContent || (
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-9 w-9 hover:bg-accent hover:text-accent-foreground">
                <Heart className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-9 w-9 hover:bg-accent hover:text-accent-foreground relative">
                <ShoppingCart className="h-4 w-4" />
                <Badge className="absolute -top-1 -right-1 h-4 w-4 rounded-full p-0 text-[10px] font-medium">0</Badge>
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleToggleDarkMode}
                className="h-9 w-9 hover:bg-accent hover:text-accent-foreground"
              >
                {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
              <div className="w-px h-6 bg-border mx-2" />
              <CustomerDropdown />
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Navbar
