import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';

interface UiState {
  searchTerm: string;
  searchCategory: 'Basic' | 'Semantic';
  darkMode: boolean;
}

const initialState: UiState = {
  searchTerm: '',
  searchCategory: 'Basic',
  darkMode: false,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setSearchTerm: (state, action: PayloadAction<string>) => {
      state.searchTerm = action.payload;
    },
    setSearchCategory: (state, action: PayloadAction<'Basic' | 'Semantic'>) => {
      state.searchCategory = action.payload;
    },
    setDarkMode: (state, action: PayloadAction<boolean>) => {
      state.darkMode = action.payload;
    },
    toggleDarkMode: (state) => {
      state.darkMode = !state.darkMode;
    },
  },
});

export const { setSearchTerm, setSearchCategory, setDarkMode, toggleDarkMode } = uiSlice.actions;
export default uiSlice.reducer;
