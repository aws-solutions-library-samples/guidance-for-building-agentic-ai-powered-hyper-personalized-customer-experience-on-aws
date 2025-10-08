export interface ApiConfig {
  baseUrl: string;
  imageBaseUrl: string;
}

// Default to same host if no base URL is provided
const getBaseUrl = (): string => {
  // Check if there's a custom base URL in environment variables
  const envBaseUrl = import.meta.env.VITE_API_BASE_URL;
  
  if (envBaseUrl) {
    return envBaseUrl;
  }
  
  // Development: Direct connection to localhost:8000 (no /api prefix)
  if (import.meta.env.DEV) {
    return 'http://localhost:8000';
  }
  
  // Production: same host with /api prefix
  return `${window.location.origin}/api`;
};

// Get the image base URL for CloudFront
const getImageBaseUrl = (): string => {
  // Check if there's a custom image base URL in environment variables
  const envImageBaseUrl = import.meta.env.VITE_IMAGE_BASE_URL;
  
  if (envImageBaseUrl) {
    return envImageBaseUrl;
  }
  
  // Always use the same origin for images since CloudFront serves both the app and images
  // The /images/* path is configured in CloudFront to serve from S3
  // Both in development and production, we use the same domain
  return window.location.origin;
};

export const apiConfig: ApiConfig = {
  baseUrl: getBaseUrl(),
  imageBaseUrl: getImageBaseUrl()
};
