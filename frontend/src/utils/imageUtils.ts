import { apiConfig } from '../config/api';

/**
 * Get the full image URL for a product
 * @param image_url - The image URL from the product data (e.g., "/images/VIT001.png")
 * @returns The complete image URL
 */
export const getProductImageUrl = (image_url?: string): string => {
  // If we have a specific image URL from the catalog, use it with CloudFront
  if (image_url) {
    // If it's already a full URL, return as-is
    if (image_url.startsWith('http://') || image_url.startsWith('https://')) {
      return image_url;
    }
    
    // If it starts with /images/, it's meant for CloudFront
    if (image_url.startsWith('/images/')) {
      return `${apiConfig.imageBaseUrl}${image_url}`;
    }
    
    // If it's just a filename, assume it goes in the /images/ path
    if (!image_url.startsWith('/')) {
      return `${apiConfig.imageBaseUrl}/images/${image_url}`;
    }
    
    // Otherwise, prepend the base URL
    return `${apiConfig.imageBaseUrl}${image_url}`;
  }
  
  // No fallback - return empty string if no image URL provided
  return '';
};


/**
 * Handle image loading errors by showing a fallback image
 * @param event - The error event from the img element
 */
export const handleImageError = (event: React.SyntheticEvent<HTMLImageElement>) => {
  const img = event.currentTarget;
  
  // Don't try to set fallback if we're already showing a fallback
  if (img.src.includes('/assets/')) {
    img.style.display = 'none';
    return;
  }
  
  // Try to determine the appropriate stock image based on the original image name
  let fallbackImage = '/assets/medical-stock.png'; // default fallback
  
  if (img.src.includes('VIT') || img.alt.toLowerCase().includes('vitamin')) {
    fallbackImage = '/assets/vitamin-stock.png';
  } else if (img.src.includes('SKIN') || img.alt.toLowerCase().includes('skin')) {
    fallbackImage = '/assets/skincare-stock.png';
  } else if (img.src.includes('OTC') || img.alt.toLowerCase().includes('medicine')) {
    fallbackImage = '/assets/otc-stock.png';
  } else if (img.src.includes('HERB') || img.alt.toLowerCase().includes('herb')) {
    fallbackImage = '/assets/herb-stock.png';
  } else if (img.src.includes('CARE') || img.alt.toLowerCase().includes('care')) {
    fallbackImage = '/assets/cream-stock.png';
  } else if (img.src.includes('FIRST') || img.alt.toLowerCase().includes('first aid')) {
    fallbackImage = '/assets/firstaid-stock.png';
  }
  
  // Set the fallback image
  img.src = fallbackImage;
};
