import { configureStore } from '@reduxjs/toolkit';
import productsReducer from './slices/productsSlice';
import uiReducer from './slices/uiSlice';
import customersReducer from './slices/customersSlice';

export const store = configureStore({
  reducer: {
    products: productsReducer,
    ui: uiReducer,
    customers: customersReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
