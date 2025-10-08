import React, { useState, useEffect } from 'react'
import { User, ChevronDown, Check, Loader2 } from 'lucide-react'
import { Button } from './ui/button'
import { Avatar, AvatarFallback } from './ui/avatar'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { fetchCustomers, loginAsCustomer, logout } from '../store/slices/customersSlice'

const CustomerDropdown: React.FC = () => {
  const dispatch = useAppDispatch()
  const { current, availableCustomers, loading, fetchingCustomers } = useAppSelector(
    (state) => state.customers
  )
  const [isOpen, setIsOpen] = useState(false)

  // Fetch customers when component mounts
  useEffect(() => {
    if (availableCustomers.length === 0) {
      dispatch(fetchCustomers())
    }
  }, [dispatch, availableCustomers.length])

  const handleCustomerSelect = async (customerId: string) => {
    await dispatch(loginAsCustomer(customerId))
    setIsOpen(false)
  }

  const handleLogout = () => {
    dispatch(logout())
    setIsOpen(false)
  }

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(part => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  return (
    <div className="relative">
      {/* Profile Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 h-8 px-2 hover:bg-muted/70 transition-colors"
      >
        <Avatar className="h-6 w-6">
          <AvatarFallback className="bg-muted text-xs">
            {current ? getInitials(current.personal_info.name) : <User className="h-3 w-3" />}
          </AvatarFallback>
        </Avatar>
        {current && (
          <span className="text-xs font-medium hidden sm:block">
            {current.personal_info.name.split(' ')[0]}
          </span>
        )}
        <ChevronDown className="h-3 w-3" />
      </Button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-80 bg-background border border-border rounded-lg shadow-lg z-50">
          <div className="p-3 border-b border-border">
            <div className="text-sm font-medium">Login Simulation</div>
            <div className="text-xs text-muted-foreground">
              Select a customer to simulate login
            </div>
          </div>

          <div className="max-h-64 overflow-y-auto">
            {/* Current User Section */}
            {current && (
              <>
                <div className="p-3 bg-muted/30">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                          {getInitials(current.personal_info.name)}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="text-sm font-medium">{current.personal_info.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {current.personal_info.address.city}, {current.personal_info.address.state}
                        </div>
                      </div>
                    </div>
                    <Check className="h-4 w-4 text-green-600" />
                  </div>
                </div>
                <div className="px-3 py-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLogout}
                    className="w-full text-xs"
                  >
                    Logout
                  </Button>
                </div>
                <div className="border-t border-border my-1" />
              </>
            )}

            {/* Available Customers */}
            <div className="p-2">
              <div className="text-xs font-medium text-muted-foreground mb-2 px-2">
                Available Customers
              </div>
              
              {fetchingCustomers ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  <span className="text-xs text-muted-foreground">Loading customers...</span>
                </div>
              ) : (
                <div className="space-y-1">
                  {availableCustomers.map((customer) => (
                    <button
                      key={customer.customer_id}
                      onClick={() => handleCustomerSelect(customer.customer_id)}
                      disabled={loading || current?.customer_id === customer.customer_id}
                      className="group w-full flex items-center gap-2 p-2 rounded-md transition-all duration-200 hover:bg-accent hover:text-accent-foreground hover:shadow-sm active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:shadow-none disabled:active:scale-100"
                    >
                      <Avatar className="h-6 w-6">
                        <AvatarFallback className="bg-muted text-xs">
                          {getInitials(customer.name)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 text-left">
                        <div className="text-xs font-medium">{customer.name}</div>
                        <div className="text-xs text-muted-foreground group-hover:text-accent-foreground/90 transition-colors">
                          {customer.city}, {customer.state}
                          {customer.age && ` • Age ${customer.age}`}
                        </div>
                      </div>
                      {loading && current?.customer_id === customer.customer_id && (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {availableCustomers.length === 0 && !fetchingCustomers && (
            <div className="p-4 text-center text-xs text-muted-foreground">
              No customers available
            </div>
          )}
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}

export default CustomerDropdown
