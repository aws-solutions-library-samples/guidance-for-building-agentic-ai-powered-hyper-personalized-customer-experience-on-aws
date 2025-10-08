import React from 'react';
import { Star, ShoppingCart, Heart, Info } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import type { Product } from '../store/types';
import { getProductImageUrl, handleImageError } from '../utils/imageUtils';

interface ProductCardBackendProps {
  product: Product;
  showSimilarity?: boolean;
  isRecommendation?: boolean;
}

const ProductCardBackend: React.FC<ProductCardBackendProps> = ({ product, showSimilarity = false, isRecommendation = false }) => {

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-all duration-200 group relative">
      {/* Wishlist Button */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity bg-background/80 hover:bg-background"
      >
        <Heart className="h-4 w-4" />
      </Button>

      <div className="aspect-square overflow-hidden bg-muted/20 relative">
        <img 
          src={getProductImageUrl(product.image_url)} 
          alt={product.name} 
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
          onError={(e) => handleImageError(e)}
        />
        {/* Stock Status Overlay */}
        {product.stock_status !== 'In Stock' && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <Badge variant="destructive" className="text-white">
              {product.stock_status}
            </Badge>
          </div>
        )}
      </div>

      <CardContent className="p-4">
        {/* Category Badge */}
        {product.category && (
          <Badge variant="secondary" className="mb-2 text-xs">
            {product.category}
          </Badge>
        )}

        {/* Product Name */}
        <h3 className="font-semibold text-base mb-1 line-clamp-2 leading-tight min-h-[2.5rem]">
          {product.name}
        </h3>

        {/* Conditional Content Based on Type */}
        {isRecommendation ? (
          <>
            {/* AI Recommendation Reason - Only for recommendations */}
            {product.description && (
              <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800">
                <p className="text-xs text-blue-800 dark:text-blue-200 leading-relaxed">
                  <span className="font-medium">Why recommended:</span> {product.description}
                </p>
              </div>
            )}
          </>
        ) : (
          <>
            {/* Brand - Only for search results */}
            <p className="text-muted-foreground text-sm mb-2 font-medium">
              {product.brand || 'Generic'}
            </p>

            {/* Rating - Only for search results */}
            <div className="flex items-center gap-1 mb-3">
              <div className="flex">
                {[...Array(5)].map((_, i) => (
                  <Star 
                    key={i} 
                    className={`w-3 h-3 ${
                      i < Math.floor(product.rating || 4.0) 
                        ? 'fill-yellow-400 text-yellow-400' 
                        : 'text-gray-300'
                    }`} 
                  />
                ))}
              </div>
              <span className="text-sm text-muted-foreground">
                {(product.rating || 4.0).toFixed(1)} ({product.reviews_count || 0})
              </span>
            </div>
          </>
        )}

        {/* Similarity Badge */}
        {showSimilarity && product.similarity !== undefined && (
          <div className="mb-3">
            <Badge variant="outline" className="text-xs">
              Match: {(product.similarity * 100).toFixed(1)}%
            </Badge>
          </div>
        )}

        {/* Price and Actions */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-bold text-xl text-primary">
                {product.currency && product.currency !== 'USD' ? `${product.currency} ` : '$'}
                {product.price.toFixed(2)}
              </p>
              {/* Stock Status - Only for search results */}
              {!isRecommendation && product.stock_status === 'In Stock' && (
                <p className="text-xs text-green-600 font-medium">✓ In Stock</p>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button 
              size="sm" 
              className="flex-1 text-xs"
              disabled={product.stock_status !== 'In Stock'}
            >
              <ShoppingCart className="h-3 w-3 mr-1" />
              Add to Cart
            </Button>
            <Button variant="outline" size="sm" className="px-2">
              <Info className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ProductCardBackend;
