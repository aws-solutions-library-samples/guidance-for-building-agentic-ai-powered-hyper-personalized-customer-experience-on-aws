import React from 'react';
import ProductCardBackend from './ProductCardBackend';
import type { Product } from '../store/types';

interface ProductRecommendationsProps {
  products: Product[];
}

const ProductRecommendations: React.FC<ProductRecommendationsProps> = ({ products }) => {
  if (!products || products.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-foreground mb-3">
        Here are recommended products for you:
      </p>
      <div className="grid gap-3">
        {products.map((product, index) => (
          <div key={product.id || index} className="w-full">
            <ProductCardBackend 
              product={product} 
              showSimilarity={product.similarity !== undefined}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProductRecommendations;
