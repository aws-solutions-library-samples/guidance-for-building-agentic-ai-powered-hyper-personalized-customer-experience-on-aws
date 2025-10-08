import boto3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
from decimal import Decimal

from config.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for DynamoDB Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

class DynamoDBService:
    """Simplified DynamoDB service with essential operations"""
    
    def __init__(self):
        """Initialize DynamoDB client and resource"""
        try:
            # Initialize with persistent session for credential management
            self._session = None
            self._initialize_clients()
            
            logger.info("DynamoDB service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB service: {str(e)}")
            raise

    def _initialize_clients(self):
        """Initialize or refresh DynamoDB clients with current credentials"""
        try:
            # Create a new session to get fresh credentials
            self._session = boto3.Session()
            
            # Use session to create clients with fresh credentials
            self.dynamodb_client = self._session.client(
                'dynamodb',
                region_name=settings.AWS_REGION
            )

            self.dynamodb_resource = self._session.resource(
                'dynamodb',
                region_name=settings.AWS_REGION
            )

            self.customers_table = self.dynamodb_resource.Table(settings.DYNAMODB_CUSTOMERS_TABLE)
            self.products_table = self.dynamodb_resource.Table(settings.DYNAMODB_PRODUCTS_TABLE)
            self.search_history_table = self.dynamodb_resource.Table(settings.DYNAMODB_SEARCH_HISTORY_TABLE)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB clients: {str(e)}")
            return False

    def _refresh_credentials_if_needed(self):
        """Check if credentials need refresh and reinitialize clients if necessary"""
        try:
            if not self._session:
                logger.info("No session found, initializing clients")
                return self._initialize_clients()
            
            # Get current credentials
            credentials = self._session.get_credentials()
            
            if not credentials:
                logger.warning("No credentials available, reinitializing clients")
                return self._initialize_clients()
            
            # Check if credentials are expired or about to expire
            if hasattr(credentials, '_expiry_time') and credentials._expiry_time:
                from datetime import datetime, timezone
                
                # If credentials expire within 5 minutes, refresh them
                current_time = datetime.now(timezone.utc)
                if credentials._expiry_time <= current_time.timestamp() + 300:
                    logger.info("Credentials expiring soon, refreshing clients")
                    return self._initialize_clients()
            
            return True
            
        except Exception as e:
            logger.warning(f"Error checking credential expiry, reinitializing: {str(e)}")
            return self._initialize_clients()

    def _ensure_clients(self):
        """Ensure DynamoDB clients are available and credentials are fresh"""
        # First check if credentials need refresh
        if not self._refresh_credentials_if_needed():
            raise ValueError("Failed to refresh AWS credentials")
            
        if not self.dynamodb_client or not self.dynamodb_resource:
            raise ValueError("DynamoDB clients not initialized. Check configuration.")

    def _convert_decimals(self, obj: Any) -> Any:
        """Convert DynamoDB Decimal types to Python types"""
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj

    def _prepare_item_for_dynamodb(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare item for DynamoDB by converting float to Decimal"""
        def convert_floats(obj):
            if isinstance(obj, dict):
                return {k: convert_floats(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_floats(list_item) for list_item in obj]
            elif isinstance(obj, float):
                return Decimal(str(obj))
            return obj
        
        return convert_floats(item)

    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer in DynamoDB"""
        try:
            self._ensure_clients()
            
            now = datetime.now().isoformat()
            customer_data['created_at'] = now
            customer_data['updated_at'] = now

            item = self._prepare_item_for_dynamodb(customer_data)

            self.customers_table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(customer_id)'
            )
            logger.info(f"Customer created successfully: {customer_data['customer_id']}")
            return self._convert_decimals(customer_data)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.error(f"Customer already exists: {customer_data.get('customer_id')}")
                raise ValueError("Customer with this ID already exists")
            else:
                logger.error(f"Failed to create customer: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error creating customer: {str(e)}")
            raise

    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer by ID"""
        try:
            self._ensure_clients()
            
            response = self.customers_table.get_item(
                Key={'customer_id': customer_id}
            )
            
            if 'Item' in response:
                logger.info(f"Customer retrieved: {customer_id}")
                return self._convert_decimals(response['Item'])
            else:
                logger.warning(f"Customer not found: {customer_id}")
                return None
                
        except ClientError as e:
            logger.error(f"Failed to get customer {customer_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting customer: {str(e)}")
            raise

    async def list_customers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all customers with basic info for dropdown"""
        try:
            self._ensure_clients()
            
            response = self.customers_table.scan(
                Limit=limit,
                Select='ALL_ATTRIBUTES'
            )
            
            customers = []
            for item in response.get('Items', []):
                customer = self._convert_decimals(item)
                # Extract minimal customer info for the dropdown
                customer_info = {
                    'customer_id': customer['customer_id'],
                    'name': customer.get('personal_info', {}).get('name', ''),
                    'email': customer.get('personal_info', {}).get('email', ''),
                    'age': customer.get('personal_info', {}).get('age'),
                    'city': customer.get('personal_info', {}).get('address', {}).get('city', ''),
                    'state': customer.get('personal_info', {}).get('address', {}).get('state', '')
                }
                customers.append(customer_info)
            
            logger.info(f"Retrieved {len(customers)} customers from DynamoDB")
            return customers
                
        except ClientError as e:
            logger.error(f"Failed to list customers: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing customers: {str(e)}")
            raise

    async def search_products(self, 
        category: Optional[str] = None,
        brand: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        limit: int = 50) -> List[Dict[str, Any]]:
        """Search products with filters"""
        try:
            self._ensure_clients()
            
            filter_expression = None
            expression_attribute_names = {}
            expression_attribute_values = {}

            conditions = []
            
            if category:
                conditions.append("#category = :category")
                expression_attribute_names["#category"] = "category"
                expression_attribute_values[":category"] = category

            if brand:
                conditions.append("#brand = :brand")
                expression_attribute_names["#brand"] = "brand"
                expression_attribute_values[":brand"] = brand

            if price_min is not None:
                conditions.append("price >= :price_min")
                expression_attribute_values[":price_min"] = Decimal(str(price_min))

            if price_max is not None:
                conditions.append("price <= :price_max")
                expression_attribute_values[":price_max"] = Decimal(str(price_max))

            scan_kwargs = {
                'Limit': limit,
                'Select': 'ALL_ATTRIBUTES'
            }

            if conditions:
                filter_expression = " AND ".join(conditions)
                scan_kwargs['FilterExpression'] = filter_expression

                if expression_attribute_names:
                    scan_kwargs['ExpressionAttributeNames'] = expression_attribute_names
                if expression_attribute_values:
                    scan_kwargs['ExpressionAttributeValues'] = expression_attribute_values

            response = self.products_table.scan(**scan_kwargs)

            products = [self._convert_decimals(item) for item in response.get('Items', [])]

            logger.info(f"Found {len(products)} products matching criteria")
            return products

        except ClientError as e:
            logger.error(f"Failed to search products: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching products: {str(e)}")
            raise

    async def save_search_history(self, search_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save search history"""
        try:
            self._ensure_clients()
            
            search_data['timestamp'] = datetime.now().isoformat()

            item = self._prepare_item_for_dynamodb(search_data)

            self.search_history_table.put_item(Item=item)

            logger.info(f"Search history saved: {search_data.get('search_id')}")
            return self._convert_decimals(search_data)

        except ClientError as e:
            logger.error(f"Failed to save search history: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving search history: {str(e)}")
            raise

    async def batch_write_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch write products to DynamoDB"""
        try:
            self._ensure_clients()
            
            with self.products_table.batch_writer() as batch:
                for product in products:
                    now = datetime.now().isoformat()
                    product['created_at'] = now
                    product['updated_at'] = now
                    item = self._prepare_item_for_dynamodb(product)
                    batch.put_item(Item=item)

            logger.info(f"Batch wrote {len(products)} products")
            return {
                'success': True,
                'products_written': len(products),
                'message': f'Successfully wrote {len(products)} products'
            }

        except ClientError as e:
            logger.error(f"Failed to batch write products: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in batch write: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, str]:
        """Check DynamoDB service health"""
        try:
            self._ensure_clients()
            
            response = self.dynamodb_client.describe_table(
                TableName=settings.DYNAMODB_CUSTOMERS_TABLE
            )

            if response['Table']['TableStatus'] == 'ACTIVE':
                return {'status': 'healthy', 'message': 'DynamoDB connection successful'}
            else:
                return {'status': 'unhealthy', 'message': f"Table status: {response['Table']['TableStatus']}"}

        except ClientError as e:
            logger.error(f"DynamoDB health check failed: {str(e)}")
            return {'status': 'unhealthy', 'message': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in health check: {str(e)}")
            return {'status': 'unhealthy', 'message': str(e)}

dynamodb_service = DynamoDBService()
