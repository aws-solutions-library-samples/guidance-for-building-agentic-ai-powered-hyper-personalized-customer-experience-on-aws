export interface Product {
  // Core required fields
  id: string;
  name: string;
  category: string;
  price: number;
  currency: string;
  description: string;
  stock_status: string;
  
  // Optional product details
  detailed_description?: string;
  brand?: string;
  
  // Product specifications
  ingredients?: string[];
  serving_size?: string;
  servings_per_container?: string | number;
  directions?: string;
  warnings?: string;
  benefits?: string[];
  certifications?: string[];
  
  // Physical attributes
  dimensions?: string;
  weight?: string;
  volume?: string;
  
  // Product-specific counts (for different product types)
  tablet_count?: number;
  gummy_count?: number;
  drop_count?: number;
  piece_count?: number;
  
  // Ratings and reviews
  rating?: number;
  reviews_count?: number;
  
  // Technical/device specifications
  battery_life?: string;
  cuff_range?: string;
  capacity?: string;
  
  // Media and search
  image_url?: string;
  searchable_text?: string;
  
  // Timestamps and metadata
  created_at?: string;
  updated_at?: string;
  indexed_at?: string;
  _score?: number;
  
  // Semantic search specific fields
  similarity?: number;
  raw_score?: number;
}

export interface SearchFilters {
  category?: string;
  subcategory?: string;
  price_min?: number;
  price_max?: number;
  in_stock?: boolean;
  brand?: string;
}

export interface SearchRequest {
  query: string;
  filters?: SearchFilters;
  from_?: number;
  size?: number;
}

export interface SearchResponse {
  success?: boolean;
  message?: string;
  data?: {
    query: string;
    total_hits: number;
    results: Product[];
    from?: number;
    size?: number;
    took_ms?: number;
    similarity_threshold?: number;
  };
  // For backward compatibility, also allow direct properties
  query?: string;
  total_hits?: number;
  results?: Product[];
  from?: number;
  size?: number;
  took_ms?: number;
}

export interface SemanticSearchRequest {
  query: string;
  filters?: SearchFilters;
  size?: number;
  similarity_threshold?: number;
}

export interface Address {
  street: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
}

export interface PersonalInfo {
  name: string;
  gender: string;
  email: string;
  address: Address;
  age?: number;
  date_of_birth?: string;
  phone?: string;
  occupation?: string;
  lifestyle?: string;
  fitness_level?: string;
  dietary_preferences?: string[];
  allergies?: string[];
  medications?: string[];
  health_goals?: string[];
}

export interface BodyComposition {
  height?: string;
  height_cm?: number;
  weight?: string;
  weight_kg?: number;
  bmi?: number;
  body_fat_percentage?: number;
  muscle_mass_percentage?: number;
  bone_density?: string;
  metabolic_rate?: number;
  waist_circumference?: string;
  blood_pressure?: string;
  resting_heart_rate?: number;
  last_measured?: string;
}

export interface BloodworkData {
  test_date?: string;
  lab_provider?: string;
  complete_blood_count?: Record<string, string | number>;
  comprehensive_metabolic_panel?: Record<string, string | number>;
  lipid_panel?: Record<string, string | number>;
  vitamins_minerals?: Record<string, string | number>;
  hormones?: Record<string, string | number>;
  inflammatory_markers?: Record<string, string | number>;
  women_specific?: Record<string, string | number>;
  diabetes_markers?: Record<string, string | number>;
  cardiac_markers?: Record<string, string | number>;
  kidney_function?: Record<string, string | number>;
}

export interface OrderHistoryItem {
  order_id: string;
  order_date: string;
  total_amount: number;
  status: string;
  items: Record<string, string | number>[];
  shipping_address?: string;
  payment_method?: string;
}

export interface PurchasePatterns {
  total_orders?: number;
  total_spent?: number;
  average_order_value?: number;
  favorite_categories?: string[];
  purchase_frequency?: string;
  preferred_brands?: string[];
  seasonal_trends?: string;
}

export interface HealthInsights {
  risk_factors?: string[];
  recommendations?: string[];
  health_score?: number;
  last_health_assessment?: string;
}

export interface Customer {
  customer_id: string;
  personal_info: PersonalInfo;
  body_composition?: BodyComposition;
  bloodwork_data?: BloodworkData;
  order_history?: OrderHistoryItem[];
  purchase_patterns?: PurchasePatterns;
  health_insights?: HealthInsights;
  created_at?: string;
  updated_at?: string;
}

export interface CustomerMinimal {
  customer_id: string;
  name: string;
  gender: string;
  email: string;
  address: Address;
}

export interface AppState {
  products: {
    items: Product[];
    loading: boolean;
    error: string | null;
    searchResults: Product[];
    totalHits: number;
    searchLoading: boolean;
    searchError: string | null;
  };
  customers: {
    current: Customer | null;
    loading: boolean;
    error: string | null;
  };
  ui: {
    searchTerm: string;
    searchCategory: 'Basic' | 'Semantic' | 'Hyper-personalized';
    darkMode: boolean;
  };
}
