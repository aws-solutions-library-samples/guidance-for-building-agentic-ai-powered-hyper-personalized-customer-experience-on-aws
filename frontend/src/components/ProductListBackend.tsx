import React from 'react';
import { Loader2 } from 'lucide-react';
import ProductCardBackend from './ProductCardBackend';
import { useAppSelector } from '../store/hooks';

const ProductListBackend: React.FC = () => {
  const { searchResults, totalHits, searchLoading, searchError, lastSearchType } = useAppSelector(
    (state) => state.products
  );

  if (searchLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Searching...</span>
      </div>
    );
  }

  if (searchError) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="text-center py-12">
          <p className="text-red-500">Search error: {searchError}</p>
        </div>
      </div>
    );
  }

  const productsToShow = searchResults && searchResults.length > 0 ? searchResults : [];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Results count */}
      {totalHits > 0 && (
        <div className="mb-6 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {totalHits} products found
          </span>
        </div>
      )}

      {/* Product Grid */}
      {productsToShow.length > 0 ? (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {productsToShow.map((product) => (
              <ProductCardBackend 
                key={product.id} 
                product={product} 
                showSimilarity={lastSearchType === 'semantic'}
              />
            ))}
          </div>
          
          {/* Results count */}
          <div className="mt-6 text-center text-muted-foreground">
            Showing {productsToShow.length} of {totalHits} products
          </div>
        </>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">
            Start typing to search for products (minimum 3 characters).
          </p>
        </div>
      )}
    </div>
  );
};

export default ProductListBackend;
