import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { MessageCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import Navbar from './Navbar';
import ProductListBackend from './ProductListBackend';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { performKeywordSearch, performSemanticSearch, clearSearchResults } from '../store/slices/productsSlice';

const SearchResults: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { searchCategory } = useAppSelector((state) => state.ui);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '');
  const [selectedCategory, setSelectedCategory] = useState(searchParams.get('category') || '');

  const categories = [
    'All Categories',
    'Vitamins',
    'Skincare',
    'Medicine',
    'Supplements',
    'Personal Care',
    'First Aid'
  ];

  useEffect(() => {
    const query = searchParams.get('q') || '';
    const category = searchParams.get('category') || '';
    setSearchQuery(query);
    setSelectedCategory(category);
    
    // Trigger search when URL params change
    if (query.trim()) {
      const filters: { category?: string } = {};
      if (category && category !== 'All Categories') {
        filters.category = category;
      }
      
      // Use semantic search if search category is "Semantic", otherwise use keyword search
      if (searchCategory === 'Semantic') {
        dispatch(performSemanticSearch({ 
          query: query.trim(),
          filters: Object.keys(filters).length > 0 ? filters : undefined
        }));
      } else {
        dispatch(performKeywordSearch({ 
          query: query.trim(),
          filters: Object.keys(filters).length > 0 ? filters : undefined
        }));
      }
    } else {
      dispatch(clearSearchResults());
    }
  }, [searchParams, dispatch, searchCategory]);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      const params = new URLSearchParams();
      params.set('q', searchQuery.trim());
      if (selectedCategory && selectedCategory !== 'All Categories') {
        params.set('category', selectedCategory);
      }
      navigate(`/search?${params.toString()}`);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleCategoryFilter = (category: string) => {
    setSelectedCategory(category);
    const params = new URLSearchParams();
    if (searchQuery.trim()) {
      params.set('q', searchQuery.trim());
    }
    if (category && category !== 'All Categories') {
      params.set('category', category);
    }
    navigate(`/search?${params.toString()}`);
  };

  const goBack = () => {
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <Navbar
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        onSearch={handleSearch}
        onKeyPress={handleKeyPress}
        showBackButton={true}
        onBackClick={goBack}
      />

      {/* Category Filters */}
      <div className="bg-muted/20 border-b border-border/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center gap-2 py-4 overflow-x-auto">
            {categories.map((category) => (
              <Button
                key={category}
                variant={selectedCategory === category || (selectedCategory === '' && category === 'All Categories') ? "default" : "ghost"}
                size="sm"
                onClick={() => handleCategoryFilter(category)}
                className="whitespace-nowrap text-sm font-medium"
              >
                {category}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Search Results */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Search Info */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-semibold tracking-tight">Search Results</h1>
            {searchQuery && (
              <Badge variant="secondary" className="text-sm font-medium">
                "{searchQuery}"
              </Badge>
            )}
            {selectedCategory && selectedCategory !== 'All Categories' && (
              <Badge variant="outline" className="text-sm">
                {selectedCategory}
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground">
            {searchQuery 
              ? `Results for "${searchQuery}"${selectedCategory && selectedCategory !== 'All Categories' ? ` in ${selectedCategory}` : ''}`
              : selectedCategory && selectedCategory !== 'All Categories' 
                ? `All products in ${selectedCategory}`
                : 'All products'
            }
          </p>
        </div>

        {/* Results */}
        <ProductListBackend />
      </main>

      {/* Floating Chat Button */}
      <Button
        onClick={() => navigate('/chat')}
        className="fixed bottom-6 right-6 h-12 w-12 rounded-full shadow-lg hover:shadow-xl transition-all duration-200 z-50 bg-accent hover:bg-accent/90"
        size="icon"
      >
        <MessageCircle className="h-5 w-5" />
      </Button>
    </div>
  );
};

export default SearchResults;
