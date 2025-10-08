import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { Product, SearchRequest, SemanticSearchRequest } from '../types';
import { apiService } from '../../services/apiService';

interface ProductsState {
  items: Product[];
  loading: boolean;
  error: string | null;
  searchResults: Product[];
  totalHits: number;
  searchLoading: boolean;
  searchError: string | null;
  lastSearchType: 'keyword' | 'semantic' | null;
}

const initialState: ProductsState = {
  items: [],
  loading: false,
  error: null,
  searchResults: [],
  totalHits: 0,
  searchLoading: false,
  searchError: null,
  lastSearchType: null,
};

// Async thunks
export const performKeywordSearch = createAsyncThunk(
  'products/keywordSearch',
  async (request: SearchRequest) => {
    const response = await apiService.keywordSearch(request);
    return response;
  }
);

export const performSemanticSearch = createAsyncThunk(
  'products/semanticSearch',
  async (request: SemanticSearchRequest) => {
    const response = await apiService.semanticSearch(request);
    return response;
  }
);


const productsSlice = createSlice({
  name: 'products',
  initialState,
  reducers: {
    clearSearchResults: (state) => {
      state.searchResults = [];
      state.totalHits = 0;
      state.searchError = null;
    },
    clearError: (state) => {
      state.error = null;
      state.searchError = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Keyword search
      .addCase(performKeywordSearch.pending, (state) => {
        state.searchLoading = true;
        state.searchError = null;
      })
      .addCase(performKeywordSearch.fulfilled, (state, action) => {
        state.searchLoading = false;
        // Handle nested response structure
        const data = action.payload.data || action.payload;
        state.searchResults = data.results || [];
        state.totalHits = data.total_hits || 0;
        state.lastSearchType = 'keyword';
      })
      .addCase(performKeywordSearch.rejected, (state, action) => {
        state.searchLoading = false;
        state.searchError = action.error.message || 'Keyword search failed';
      })
      // Semantic search
      .addCase(performSemanticSearch.pending, (state) => {
        state.searchLoading = true;
        state.searchError = null;
      })
      .addCase(performSemanticSearch.fulfilled, (state, action) => {
        state.searchLoading = false;
        // Handle nested response structure
        const data = action.payload.data || action.payload;
        state.searchResults = data.results || [];
        state.totalHits = data.total_hits || 0;
        state.lastSearchType = 'semantic';
      })
      .addCase(performSemanticSearch.rejected, (state, action) => {
        state.searchLoading = false;
        state.searchError = action.error.message || 'Semantic search failed';
      })
  },
});

export const { clearSearchResults, clearError } = productsSlice.actions;
export default productsSlice.reducer;
