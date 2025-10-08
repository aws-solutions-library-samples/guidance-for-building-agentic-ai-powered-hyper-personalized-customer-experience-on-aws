import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import type { Customer } from '../types'
import { apiService } from '../../services/apiService'

interface CustomerMinimal {
  customer_id: string
  name: string
  email: string
  age?: number
  city: string
  state: string
}

interface CustomersState {
  current: Customer | null
  availableCustomers: CustomerMinimal[]
  loading: boolean
  error: string | null
  fetchingCustomers: boolean
}

const initialState: CustomersState = {
  current: null,
  availableCustomers: [],
  loading: false,
  error: null,
  fetchingCustomers: false,
}

// Async thunk to fetch available customers for dropdown
export const fetchCustomers = createAsyncThunk(
  'customers/fetchCustomers',
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiService.getCustomers()
      // Handle the APIResponse structure from backend
      const apiResponse = response as { data: { customers: CustomerMinimal[] } }
      return apiResponse.data.customers
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch customers'
      return rejectWithValue(message)
    }
  }
)

// Async thunk to fetch detailed customer data
export const fetchCustomerDetails = createAsyncThunk(
  'customers/fetchCustomerDetails',
  async (customerId: string, { rejectWithValue }) => {
    try {
      const response = await apiService.getCustomer(customerId)
      // Handle the APIResponse structure from backend
      const apiResponse = response as { data: { customer: Customer } }
      return apiResponse.data.customer
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch customer details'
      return rejectWithValue(message)
    }
  }
)

// Async thunk to "login" as a customer (select and fetch details)
export const loginAsCustomer = createAsyncThunk(
  'customers/loginAsCustomer',
  async (customerId: string, { rejectWithValue }) => {
    try {
      const response = await apiService.getCustomer(customerId)
      // Handle the APIResponse structure from backend
      const apiResponse = response as { data: { customer: Customer } }
      return apiResponse.data.customer
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to login as customer'
      return rejectWithValue(message)
    }
  }
)

const customersSlice = createSlice({
  name: 'customers',
  initialState,
  reducers: {
    logout: (state) => {
      state.current = null
      state.error = null
    },
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch customers
      .addCase(fetchCustomers.pending, (state) => {
        state.fetchingCustomers = true
        state.error = null
      })
      .addCase(fetchCustomers.fulfilled, (state, action) => {
        state.fetchingCustomers = false
        state.availableCustomers = action.payload
        state.error = null
      })
      .addCase(fetchCustomers.rejected, (state, action) => {
        state.fetchingCustomers = false
        state.error = action.payload as string
      })
      
      // Fetch customer details
      .addCase(fetchCustomerDetails.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchCustomerDetails.fulfilled, (state, action) => {
        state.loading = false
        state.current = action.payload
        state.error = null
      })
      .addCase(fetchCustomerDetails.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      
      // Login as customer
      .addCase(loginAsCustomer.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(loginAsCustomer.fulfilled, (state, action) => {
        state.loading = false
        state.current = action.payload
        state.error = null
      })
      .addCase(loginAsCustomer.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
  },
})

export const { logout, clearError } = customersSlice.actions
export default customersSlice.reducer
