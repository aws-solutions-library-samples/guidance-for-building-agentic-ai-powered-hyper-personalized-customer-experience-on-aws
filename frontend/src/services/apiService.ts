import axios from 'axios';
import type { AxiosInstance, AxiosResponse } from 'axios';
import { apiConfig } from '../config/api';
import type { 
  SearchRequest, 
  SearchResponse, 
  SemanticSearchRequest, 
  Customer 
} from '../store/types';

interface APIResponse<T = unknown> {
  message: string;
  data: T;
}


class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: apiConfig.baseUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        return config;
      },
      (error) => {
        console.error('Request error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => {
        return response;
      },
      (error) => {
        console.error('Response error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck(): Promise<{ status: string; services: Record<string, string> }> {
    const response: AxiosResponse<{ status: string; services: Record<string, string> }> = 
      await this.api.get('/health');
    return response.data;
  }

  // Keyword search
  async keywordSearch(request: SearchRequest): Promise<SearchResponse> {
    const response: AxiosResponse<SearchResponse> = await this.api.post('/search/keyword', request);
    return response.data;
  }

  // Semantic search
  async semanticSearch(request: SemanticSearchRequest): Promise<SearchResponse> {
    const response: AxiosResponse<SearchResponse> = await this.api.post('/search/semantic', request);
    return response.data;
  }


  // Customer operations
  async createCustomer(customerData: Omit<Customer, 'customer_id' | 'created_at' | 'updated_at'>): Promise<Customer> {
    const response: AxiosResponse<Customer> = await this.api.post('/customers', customerData);
    return response.data;
  }

  async getCustomers(): Promise<APIResponse> {
    const response: AxiosResponse<APIResponse> = await this.api.get('/customers');
    return response.data;
  }

  async getCustomer(customerId: string): Promise<APIResponse> {
    const response: AxiosResponse<APIResponse> = await this.api.get(`/customers/${customerId}`);
    return response.data;
  }

}

export const apiService = new ApiService();
