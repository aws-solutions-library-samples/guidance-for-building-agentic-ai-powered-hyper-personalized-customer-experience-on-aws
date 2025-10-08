import React from 'react';
import { Star } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { type Product } from '../store/types';
import { getProductImageUrl, handleImageError } from '../utils/imageUtils';

interface ProductCardProps {
  product: Product;
  showSimilarity?: boolean;
}

const ProductCard: React.FC<ProductCardProps> = ({ product, showSimilarity = false }) => {
  return (
    <Card className="group cursor-pointer border-0 bg-background shadow-sm hover:shadow-md transition-all duration-300">
      <div className="aspect-square overflow-hidden bg-muted/30 rounded-t-lg">
        <img 
          src={getProductImageUrl(product.image_url)} 
          alt={product.name} 
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          onError={(e) => handleImageError(e)}
        />
      </div>
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <Badge variant="secondary" className="text-xs font-medium">
            {product.category || 'Product'}
          </Badge>
          {showSimilarity && product.similarity !== undefined && (
            <Badge variant="outline" className="text-xs">
              {(product.similarity * 100).toFixed(0)}% match
            </Badge>
          )}
        </div>
        
        <h3 className="font-medium text-base mb-1 line-clamp-2 leading-snug">
          {product.name}
        </h3>
        <p className="text-muted-foreground text-sm mb-3">{product.brand}</p>
        
        <div className="flex items-center gap-2 mb-4">
          <div className="flex items-center">
            <Star className="w-3 h-3 fill-yellow-400 text-yellow-400 mr-1" />
            <span className="text-sm font-medium">{product.rating}</span>
          </div>
          <span className="text-xs text-muted-foreground">
            ({product.reviews_count})
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex flex-col">
            <p className="font-semibold text-lg">
              ${product.price.toFixed(2)}
            </p>
            <Badge 
              variant={product.stock_status === 'In Stock' ? 'default' : 'secondary'}
              className="text-xs w-fit"
            >
              {product.stock_status}
            </Badge>
          </div>
          <Button size="sm" variant="outline" className="text-xs">
            Add to Cart
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default ProductCard;
