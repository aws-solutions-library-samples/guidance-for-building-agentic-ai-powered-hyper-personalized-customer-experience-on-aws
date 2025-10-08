import type { Product } from '../data/product';
import type { Product as BackendProduct } from '../store/types';

// Define types for the catalog data structure
interface CatalogProduct {
  id: string;
  name: string;
  category: string;
  brand?: string;
  price: number;
  currency?: string;
  image_url?: string;
  description: string;
  stock_status: string;
  rating?: number;
  reviews_count?: number;
}

interface CatalogData {
  catalog_info: {
    name: string;
    version: string;
    created_date: string;
    total_products: number;
    categories: string[];
  };
  products: CatalogProduct[];
}

// Import the healthcare product catalog data with proper typing
import catalogDataImport from '../data/healthcare_product_catalog.json';

const catalogData: CatalogData = catalogDataImport as CatalogData;

/**
 * Get product by ID and return it in the standardized Product format
 * @param productId - The product ID to look up
 * @returns Product with all required attributes or null if not found
 */
export const getProductById = (productId: string): Product | null => {
  // First, try to find the product in the catalog data
  const catalogProduct = catalogData.products.find((p: CatalogProduct) => p.id === productId);
  
  if (catalogProduct) {
    return mapCatalogProductToStandardProduct(catalogProduct);
  }
  
  // If not found in catalog, return null
  return null;
};

/**
 * Map a catalog product to the standardized Product interface
 * @param catalogProduct - Product from the healthcare catalog
 * @returns Standardized Product object
 */
const mapCatalogProductToStandardProduct = (catalogProduct: CatalogProduct): Product => {
  return {
    id: catalogProduct.id,
    name: catalogProduct.name,
    image_url: catalogProduct.image_url || `/images/${catalogProduct.id}.png`,
    category: catalogProduct.category,
    brand: catalogProduct.brand || 'Generic',
    price: catalogProduct.price,
    description: catalogProduct.description,
    stock_status: catalogProduct.stock_status === 'In Stock' ? 'In Stock' : 'Out of Stock',
    rating: catalogProduct.rating || 4.0,
    reviews_count: catalogProduct.reviews_count || 0,
    currency: catalogProduct.currency || 'USD'
  };
};

/**
 * Map a backend product (from API/WebSocket) to the standardized Product interface
 * @param backendProduct - Product from backend API
 * @returns Standardized Product object
 */
export const mapBackendProductToStandardProduct = (backendProduct: BackendProduct): Product => {
  return {
    id: backendProduct.id,
    name: backendProduct.name,
    image_url: backendProduct.image_url || `/images/${backendProduct.id}.png`,
    category: backendProduct.category,
    brand: backendProduct.brand || 'Generic',
    price: typeof backendProduct.price === 'number' ? backendProduct.price : 0,
    description: backendProduct.description,
    stock_status: backendProduct.stock_status === 'In Stock' ? 'In Stock' : 'Out of Stock',
    rating: typeof backendProduct.rating === 'number' ? backendProduct.rating : 4.0,
    reviews_count: typeof backendProduct.reviews_count === 'number' ? backendProduct.reviews_count : 0,
    currency: backendProduct.currency || 'USD'
  };
};

/**
 * Get multiple products by their IDs
 * @param productIds - Array of product IDs to look up
 * @returns Array of Products (excludes any not found)
 */
export const getProductsByIds = (productIds: string[]): Product[] => {
  return productIds
    .map(id => getProductById(id))
    .filter((product): product is Product => product !== null);
};

/**
 * Search products by category
 * @param category - Category to search for
 * @returns Array of Products in that category
 */
export const getProductsByCategory = (category: string): Product[] => {
  return catalogData.products
    .filter((p: CatalogProduct) => p.category.toLowerCase().includes(category.toLowerCase()))
    .map(mapCatalogProductToStandardProduct);
};

/**
 * Get all available product categories
 * @returns Array of unique category names
 */
export const getAllCategories = (): string[] => {
  const categories = catalogData.products.map((p: CatalogProduct) => p.category);
  return [...new Set(categories)].sort();
};

/**
 * Get featured products (top-rated products from each category)
 * @param limit - Maximum number of products to return (default: 4)
 * @returns Array of featured Products
 */
export const getFeaturedProducts = (limit: number = 4): Product[] => {
  const categories = getAllCategories();
  const featuredProducts: Product[] = [];
  
  for (const category of categories) {
    const categoryProducts = catalogData.products
      .filter((p: CatalogProduct) => p.category === category)
      .sort((a: CatalogProduct, b: CatalogProduct) => (b.rating || 0) - (a.rating || 0));
    
    if (categoryProducts.length > 0) {
      featuredProducts.push(mapCatalogProductToStandardProduct(categoryProducts[0]));
    }
    
    if (featuredProducts.length >= limit) break;
  }
  
  return featuredProducts.slice(0, limit);
};
