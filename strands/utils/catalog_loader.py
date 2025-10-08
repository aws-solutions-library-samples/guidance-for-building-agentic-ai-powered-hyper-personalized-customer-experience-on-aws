import json
import logging
import re
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from tqdm import tqdm

from services.dynamodb_service import dynamodb_service
from services.opensearch_service import opensearch_service
from services.bedrock_service import bedrock_service

logger = logging.getLogger(__name__)

class CatalogLoader:
    """Utility class for loading and processing product catalog and customer data"""
    def __init__(self):
        # Get the current file's directory and find the strands directory
        current_dir = Path(__file__).parent.parent  # Go up from utils/ to strands/
        
        # Try multiple possible paths for the catalog file
        possible_paths = [
            current_dir / "data" / "healthcare_product_catalog.json",  # strands/data/
            Path("/app/data/healthcare_product_catalog.json"),  # Docker container path
            Path("./data/healthcare_product_catalog.json"),   # Current directory
            Path("../data/healthcare_product_catalog.json"),  # Original path
            Path("data/healthcare_product_catalog.json"),     # From project root
            Path("strands/data/healthcare_product_catalog.json"),  # From project root to strands/data
        ]
        
        self.catalog_file_path = None
        for path in possible_paths:
            if path.exists():
                self.catalog_file_path = path
                break
        
        if not self.catalog_file_path:
            # Default to the strands/data path if none found
            self.catalog_file_path = current_dir / "data" / "healthcare_product_catalog.json"

        # Try multiple possible paths for the customer profiles file
        customer_possible_paths = [
            current_dir / "data" / "customer_profiles.json",  # strands/data/
            Path("/app/data/customer_profiles.json"),  # Docker container path
            Path("./data/customer_profiles.json"),   # Current directory
            Path("../data/customer_profiles.json"),  # Original path
            Path("data/customer_profiles.json"),     # From project root
            Path("strands/data/customer_profiles.json"),  # From project root to strands/data
        ]
        
        self.customer_profiles_file_path = None
        for path in customer_possible_paths:
            if path.exists():
                self.customer_profiles_file_path = path
                break
        
        if not self.customer_profiles_file_path:
            # Default to the strands/data path if none found
            self.customer_profiles_file_path = current_dir / "data" / "customer_profiles.json"

    async def load_catalog_from_file(self) -> Dict[str, Any]:
        """Load catalog data from JSON file"""
        try:
            if not self.catalog_file_path.exists():
                raise FileNotFoundError(f"Catalog file not found: {self.catalog_file_path}")
            with open(self.catalog_file_path, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)
            logger.info(f"Loaded catalog with {len(catalog_data.get('products', []))} products")
            return catalog_data

        except Exception as e:
            logger.error(f"Failed to load catalog from file: {str(e)}")
            raise

    async def load_customer_profiles_from_file(self) -> Dict[str, Any]:
        """Load customer profiles data from JSON file"""
        try:
            if not self.customer_profiles_file_path.exists():
                raise FileNotFoundError(f"Customer profiles file not found: {self.customer_profiles_file_path}")
            with open(self.customer_profiles_file_path, 'r', encoding='utf-8') as f:
                customer_data = json.load(f)
            
            customers = customer_data.get('customer_profiles', {}).get('customers', [])
            logger.info(f"Loaded customer profiles with {len(customers)} customers")
            return customer_data

        except Exception as e:
            logger.error(f"Failed to load customer profiles from file: {str(e)}")
            raise

    def _transform_customer_data(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Transform customer data for DynamoDB storage"""
        # Create a copy to avoid modifying the original
        transformed_customer = customer.copy()
        
        # Ensure required fields exist
        if 'customer_id' not in transformed_customer:
            raise ValueError("Customer data must include customer_id")
        
        # Flatten nested structures for easier querying if needed
        # Keep the original structure but add some computed fields for convenience
        
        # Add computed fields from personal_info for easier querying
        personal_info = transformed_customer.get('personal_info', {})
        if personal_info:
            transformed_customer['name'] = personal_info.get('name')
            transformed_customer['email'] = personal_info.get('email')
            transformed_customer['age'] = personal_info.get('age')
            transformed_customer['gender'] = personal_info.get('gender')
            transformed_customer['city'] = personal_info.get('address', {}).get('city')
            transformed_customer['state'] = personal_info.get('address', {}).get('state')
            transformed_customer['health_goals'] = personal_info.get('health_goals', [])
            transformed_customer['dietary_preferences'] = personal_info.get('dietary_preferences', [])
            transformed_customer['allergies'] = personal_info.get('allergies', [])
            transformed_customer['medications'] = personal_info.get('medications', [])
        
        # Add computed fields from purchase_patterns for easier querying
        purchase_patterns = transformed_customer.get('purchase_patterns', {})
        if purchase_patterns:
            transformed_customer['total_orders'] = purchase_patterns.get('total_orders', 0)
            transformed_customer['total_spent'] = purchase_patterns.get('total_spent', 0.0)
            transformed_customer['average_order_value'] = purchase_patterns.get('average_order_value', 0.0)
            transformed_customer['favorite_categories'] = purchase_patterns.get('favorite_categories', [])
            transformed_customer['preferred_brands'] = purchase_patterns.get('preferred_brands', [])
        
        # Add health score for easier filtering
        health_insights = transformed_customer.get('health_insights', {})
        if health_insights:
            transformed_customer['health_score'] = health_insights.get('health_score', 0)
            transformed_customer['risk_factors'] = health_insights.get('risk_factors', [])
        
        return transformed_customer

    async def load_customers_to_dynamodb(self, customers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Load customers to DynamoDB"""
        try:
            successful_loads = 0
            failed_loads = 0
            errors = []

            for customer in tqdm(customers, desc="Loading customers to DynamoDB"):
                try:
                    # Transform customer data
                    transformed_customer = self._transform_customer_data(customer)
                    
                    # Create customer in DynamoDB
                    await dynamodb_service.create_customer(transformed_customer)
                    successful_loads += 1
                    
                except Exception as e:
                    failed_loads += 1
                    error_msg = f"Failed to load customer {customer.get('customer_id', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)

            result = {
                'success': failed_loads == 0,
                'customers_written': successful_loads,
                'customers_failed': failed_loads,
                'total_customers': len(customers),
                'errors': errors
            }

            logger.info(f"Customer load completed: {successful_loads} successful, {failed_loads} failed")
            return result

        except Exception as e:
            logger.error(f"Failed to load customers to DynamoDB: {str(e)}")
            raise

    async def full_customer_load(self) -> Dict[str, Any]:
        """Perform full customer load to DynamoDB"""
        try:
            customer_data = await self.load_customer_profiles_from_file()
            customers = customer_data.get('customer_profiles', {}).get('customers', [])

            if not customers:
                raise ValueError("No customers found in customer profiles")

            dynamodb_result = await self.load_customers_to_dynamodb(customers)

            result = {
                "success": dynamodb_result.get('success', False),
                "total_customers": len(customers),
                "profile_info": customer_data.get('customer_profiles', {}).get('profile_info', {}),
                "dynamodb_result": dynamodb_result
            }

            logger.info(f"Full customer load completed: {len(customers)} customers")
            return result
            
        except Exception as e:
            logger.error(f"Full customer load failed: {str(e)}")
            raise
    
    async def process_products_for_search(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process products for search indexing by generating embeddings"""
        try:
            processed_products = []
            for product in tqdm(products):
                # Transform product data to match frontend expectations
                processed_product = self._transform_product_data(product)
                
                searchable_text = self._create_searchable_text(processed_product)
                try:
                    embedding = await bedrock_service.generate_embeddings(searchable_text)
                    asyncio.sleep(0.5)
                    processed_product['embedding'] = embedding
                    processed_product['searchable_text'] = searchable_text
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for product {processed_product.get('id')}: {str(e)}")
                    processed_product['embedding'] = []
                    processed_product['searchable_text'] = searchable_text

                processed_products.append(processed_product)

            logger.info(f"Processed {len(processed_products)} products for search")
            return processed_products

        except Exception as e:
            logger.error(f"Failed to process products for search: {str(e)}")
            raise
    
    def _transform_product_data(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Transform product data to match frontend expectations"""
        # Create a copy to avoid modifying the original
        transformed_product = product.copy()
        
        # Transform stock_status to in_stock boolean
        if 'stock_status' in transformed_product:
            stock_status = transformed_product['stock_status']
            if isinstance(stock_status, str):
                # Convert string stock status to boolean
                transformed_product['in_stock'] = stock_status.lower() in ['in stock', 'available', 'yes', 'true']
            else:
                # If it's already a boolean or other type, keep as is
                transformed_product['in_stock'] = bool(stock_status)
        else:
            # Default to True if no stock status is provided
            transformed_product['in_stock'] = True
        
        # Ensure product_id field exists (some products might use 'id' instead)
        if 'id' in transformed_product and 'product_id' not in transformed_product:
            transformed_product['product_id'] = transformed_product['id']
        elif 'product_id' not in transformed_product and 'id' not in transformed_product:
            # Generate a product_id if neither exists
            transformed_product['product_id'] = f"PROD_{hash(transformed_product.get('name', 'unknown'))}"
        
        # Ensure required fields have default values
        if 'rating' not in transformed_product:
            transformed_product['rating'] = 4.0
        
        if 'reviews_count' not in transformed_product:
            transformed_product['reviews_count'] = 0
            
        # Convert price to float if it's a string
        if 'price' in transformed_product and isinstance(transformed_product['price'], str):
            try:
                transformed_product['price'] = float(transformed_product['price'])
            except (ValueError, TypeError):
                transformed_product['price'] = 0.0
        
        # Ensure image_url is a relative path for CloudFront
        if 'image_url' in transformed_product:
            image_url = transformed_product['image_url']
            if isinstance(image_url, str):
                # If it's a full S3 URL, convert it back to relative path
                if 's3.amazonaws.com' in image_url or 's3-' in image_url:
                    # Extract the path after /images/
                    match = re.search(r'/images/([^?]+)', image_url)
                    if match:
                        transformed_product['image_url'] = f"/images/{match.group(1)}"
                        logger.info(f"Converted S3 URL to relative path: {image_url} -> {transformed_product['image_url']}")
                    else:
                        # Fallback: ensure it starts with /images/
                        if not image_url.startswith('/images/'):
                            transformed_product['image_url'] = f"/images/{image_url}"
                # Ensure relative paths start with /images/
                elif not image_url.startswith('/images/') and not image_url.startswith('http'):
                    transformed_product['image_url'] = f"/images/{image_url}"
        
        return transformed_product
    
    def _create_searchable_text(self, product: Dict[str, Any]) -> str:
        """Create searchable text from product data"""
        text_parts = []

        if product.get('name'):
            text_parts.append(product['name'])

        if product.get('description'):
            text_parts.append(product['description'])

        if product.get('detailed_description'):
            text_parts.append(product['detailed_description'])

        if product.get('category'):
            text_parts.append(f"Category: {product['category']}")
        
        if product.get('brand'):
            text_parts.append(f"Brand: {product['brand']}")

        ingredients = product.get('ingredients', [])
        if ingredients:
            text_parts.append(f"Ingredients: {', '.join(ingredients)}")

        benefits = product.get('benefits', [])
        if benefits:
            text_parts.append(f"Benefits: {', '.join(benefits)}")

        certifications = product.get('certifications', [])
        if certifications:
            text_parts.append(f"Certifications: {', '.join(certifications)}")

        return ' '.join(text_parts)
    
    async def load_to_dynamodb(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Load products to DynamoDB"""
        try:
            result = await dynamodb_service.batch_write_products(products)
            logger.info(f"Loaded {result.get('products_written', 0)} products to DynamoDB")
            return result

        except Exception as e:
            logger.error(f"Failed to load products to DynamoDB: {str(e)}")
            raise
    
    async def load_to_opensearch(self, products: List[Dict[str, Any]], vpc_mode: bool = False) -> Dict[str, Any]:
        """Load products to OpenSearch with VPC connectivity handling"""
        try:
            await opensearch_service.create_index()
            result = await opensearch_service.bulk_index_products(products)
            logger.info(f"Indexed {result.get('successful', 0)} products to OpenSearch")
            return result

        except Exception as e:
            error_msg = str(e).lower()
            # Check if this is a VPC connectivity issue
            if any(keyword in error_msg for keyword in ['connection refused', 'connection error', 'timeout', 'network', 'unreachable']):
                if vpc_mode:
                    logger.warning(f"OpenSearch VPC connectivity issue detected, skipping OpenSearch indexing: {str(e)}")
                    return {
                        "success": False,
                        "vpc_connectivity_issue": True,
                        "total_products": len(products),
                        "successful": 0,
                        "failed": len(products),
                        "error": "VPC connectivity issue - OpenSearch not accessible from current network location"
                    }
                else:
                    logger.error(f"Failed to load products to OpenSearch: {str(e)}")
                    raise
            else:
                logger.error(f"Failed to load products to OpenSearch: {str(e)}")
                raise
    
    async def full_catalog_load(self, vpc_mode: bool = False) -> Dict[str, Any]:
        """Perform full catalog load to both DynamoDB and OpenSearch with VPC support"""
        try:
            catalog_data = await self.load_catalog_from_file()
            products = catalog_data.get('products', [])

            if not products:
                raise ValueError("No products found in catalog")

            processed_products = await self.process_products_for_search(products)
            dynamodb_result = await self.load_to_dynamodb(processed_products)
            opensearch_result = await self.load_to_opensearch(processed_products, vpc_mode=vpc_mode)

            # Determine overall success - if in VPC mode and OpenSearch fails due to connectivity, still consider success if DynamoDB worked
            overall_success = dynamodb_result.get('success', False)
            if vpc_mode and opensearch_result.get('vpc_connectivity_issue', False):
                logger.info("VPC mode: DynamoDB load successful, OpenSearch skipped due to VPC connectivity")
                overall_success = dynamodb_result.get('success', False)
            else:
                overall_success = dynamodb_result.get('success', False) and opensearch_result.get('success', False)

            result = {
                "success": overall_success,
                "total_products": len(products),
                "catalog_info": catalog_data.get('catalog_info', {}),
                "dynamodb_result": dynamodb_result,
                "opensearch_result": opensearch_result,
                "vpc_mode": vpc_mode
            }

            logger.info(f"Full catalog load completed: {len(products)} products (VPC mode: {vpc_mode})")
            return result
            
        except Exception as e:
            logger.error(f"Full catalog load failed: {str(e)}")
            raise
    
    async def search_products_by_query(self, 
                                     query: str,
                                     search_type: str = "keyword",
                                     filters: Optional[Dict[str, Any]] = None,
                                     size: int = 10) -> Dict[str, Any]:
        """Search products using different search methods"""
        try:
            if search_type == "semantic":
                query_embedding = await bedrock_service.generate_embeddings(query)
                results = await opensearch_service.semantic_search(
                    query_embedding=query_embedding,
                    filters=filters,
                    size=size
                )
                results['search_type'] = 'semantic'
                
            else:
                results = await opensearch_service.search_products(
                    query=query,
                    filters=filters,
                    size=size
                )
                results['search_type'] = 'keyword'
            
            logger.info(f"Search completed: {results.get('total_hits', 0)} results for '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Product search failed: {str(e)}")
            raise
    

    async def full_data_load(self, load_products: bool = True, load_customers: bool = True, vpc_mode: bool = None) -> Dict[str, Any]:
        """Perform full data load including products and customers with VPC support"""
        try:
            # Auto-detect VPC mode if not specified
            if vpc_mode is None:
                vpc_mode = await self._detect_vpc_mode()
            
            results = {
                "success": True,
                "products_loaded": False,
                "customers_loaded": False,
                "errors": [],
                "vpc_mode": vpc_mode
            }

            # Load products if requested
            if load_products:
                try:
                    print("\n🚀 Loading products...")
                    product_result = await self.full_catalog_load(vpc_mode=vpc_mode)
                    results["product_result"] = product_result
                    results["products_loaded"] = product_result.get("success", False)
                    
                    # Show VPC-specific messaging
                    if vpc_mode and product_result.get("opensearch_result", {}).get("vpc_connectivity_issue", False):
                        print(f"✅ Products loaded to DynamoDB: {product_result.get('total_products', 0)} products")
                        print(f"⚠️  OpenSearch skipped due to VPC connectivity (expected in VPC mode)")
                    else:
                        print(f"✅ Products loaded: {product_result.get('total_products', 0)} products")
                except Exception as e:
                    error_msg = f"Product load failed: {str(e)}"
                    results["errors"].append(error_msg)
                    results["success"] = False
                    logger.error(error_msg)

            # Load customers if requested
            if load_customers:
                try:
                    print("\n👥 Loading customers...")
                    customer_result = await self.full_customer_load()
                    results["customer_result"] = customer_result
                    results["customers_loaded"] = customer_result.get("success", False)
                    print(f"✅ Customers loaded: {customer_result.get('total_customers', 0)} customers")
                except Exception as e:
                    error_msg = f"Customer load failed: {str(e)}"
                    results["errors"].append(error_msg)
                    results["success"] = False
                    logger.error(error_msg)

            # Overall success depends on requested operations
            if load_products and load_customers:
                results["success"] = results["products_loaded"] and results["customers_loaded"]
            elif load_products:
                results["success"] = results["products_loaded"]
            elif load_customers:
                results["success"] = results["customers_loaded"]

            logger.info(f"Full data load completed. Products: {results['products_loaded']}, Customers: {results['customers_loaded']}")
            return results
            
        except Exception as e:
            logger.error(f"Full data load failed: {str(e)}")
            raise

    async def _detect_vpc_mode(self) -> bool:
        """Auto-detect if we're running in VPC mode"""
        try:
            import os
            import urllib.request
            
            # Check environment variables that indicate VPC execution
            vpc_indicators = [
                'AWS_EXECUTION_ENV',  # Set in Lambda/Fargate
                'ECS_CONTAINER_METADATA_URI',  # Set in ECS
                'AWS_LAMBDA_FUNCTION_NAME'  # Set in Lambda
            ]
            
            for indicator in vpc_indicators:
                if os.getenv(indicator):
                    logger.info(f"VPC mode detected via environment variable: {indicator}")
                    return True
            
            # Try to access EC2 metadata service (available in EC2/ECS/Fargate)
            try:
                req = urllib.request.Request('http://169.254.169.254/latest/meta-data/instance-id')
                req.add_header('X-aws-ec2-metadata-token-ttl-seconds', '21600')
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status == 200:
                        logger.info("VPC mode detected via EC2 metadata service")
                        return True
            except:
                pass
            
            # Check if OpenSearch endpoint is VPC-based
            try:
                from config.settings import get_settings
                settings = get_settings()
                opensearch_endpoint = settings.OPENSEARCH_ENDPOINT
                if opensearch_endpoint and 'vpc-' in opensearch_endpoint:
                    logger.info("VPC mode detected via VPC OpenSearch endpoint")
                    return True
            except:
                pass
            
            logger.info("VPC mode not detected - using standard mode")
            return False
            
        except Exception as e:
            logger.warning(f"Error detecting VPC mode, defaulting to False: {str(e)}")
            return False

catalog_loader = CatalogLoader()
