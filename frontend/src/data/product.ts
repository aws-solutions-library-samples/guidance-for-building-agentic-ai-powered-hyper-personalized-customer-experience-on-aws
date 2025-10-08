export interface Product {
  id: string;
  name: string;
  image_url: string;
  category: string;
  brand: string;
  price: number;
  description: string;
  stock_status: "In Stock" | "Out of Stock";
  rating: number;
  reviews_count: number;
  currency: string;
}
