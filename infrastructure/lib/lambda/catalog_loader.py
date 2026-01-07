import json
import boto3
import logging
import sys
import subprocess
from typing import Dict, Any, List

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to load the product catalog after CDK deployment
    """
    try:
        request_type = event['RequestType']
        logger.info(f"Request type: {request_type}")
        
        if request_type == 'Create' or request_type == 'Update':
            # Only run catalog load on Create or Update, not Delete
            result = load_catalog(event.get('ResourceProperties', {}))
            
            return {
                'Status': 'SUCCESS',
                'PhysicalResourceId': 'catalog-loader-resource',
                'Data': result
            }
        elif request_type == 'Delete':
            # Nothing to do on delete
            return {
                'Status': 'SUCCESS',
                'PhysicalResourceId': 'catalog-loader-resource',
                'Data': {'message': 'Catalog loader resource deleted'}
            }
            
    except Exception as e:
        logger.error(f"Error in catalog loader: {str(e)}")
        return {
            'Status': 'FAILED',
            'PhysicalResourceId': 'catalog-loader-resource',
            'Reason': str(e)
        }

def load_catalog(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load the product catalog to DynamoDB and OpenSearch
    """
    logger.info("Starting catalog load process...")
    
    # Install required packages
    try:
        # Use static python3 path instead of sys.executable for security
        subprocess.check_call([
            "/usr/bin/python3", "-m", "pip", "install", 
            "opensearch-py", "requests-aws4auth", "tqdm", "--target", "/tmp"
        ], shell=False)
        sys.path.insert(0, '/tmp')
    except Exception as e:
        logger.warning(f"Failed to install packages: {e}")
    
    # Get configuration from properties
    opensearch_endpoint = properties.get('OPENSEARCH_ENDPOINT')
    region = properties.get('AWS_REGION', 'us-west-2')
    products_table = properties.get('PRODUCTS_TABLE', 'products')
    index_name = properties.get('INDEX_NAME', 'products')
    bedrock_model = properties.get('BEDROCK_MODEL', 'anthropic.claude-3-7-sonnet-20250219-v1:0')
    
    logger.info(f"Configuration: endpoint={opensearch_endpoint}, region={region}, table={products_table}")
    
    # Load the product catalog
    catalog_data = load_catalog()
    logger.info(f"Loaded {len(catalog_data)} products from catalog")
    
    # Process products and generate embeddings
    processed_products = []
    bedrock_client = boto3.client('bedrock-runtime', region_name=region)
    
    for product in catalog_data:
        try:
            # Generate embedding for the product
            embedding_text = f"{product.get('name', '')} {product.get('description', '')} {product.get('category', '')}"
            embedding = generate_embedding(bedrock_client, embedding_text, bedrock_model)
            
            # Prepare product for storage
            processed_product = {
                'id': product.get('id', ''),
                'name': product.get('name', ''),
                'description': product.get('description', ''),
                'category': product.get('category', ''),
                'price': product.get('price', 0),
                'image_url': product.get('image_url', ''),
                'embedding': embedding
            }
            processed_products.append(processed_product)
            
        except Exception as e:
            logger.error(f"Error processing product {product.get('id', 'unknown')}: {e}")
            continue
    
    logger.info(f"Processed {len(processed_products)} products with embeddings")
    
    # Load to DynamoDB
    dynamodb_count = load_to_dynamodb(processed_products, products_table, region)
    logger.info(f"Loaded {dynamodb_count} products to DynamoDB")
    
    # Load to OpenSearch
    opensearch_count = load_to_opensearch(processed_products, opensearch_endpoint, index_name, region)
    logger.info(f"Loaded {opensearch_count} products to OpenSearch")
    
    return {
        'message': 'Catalog loaded successfully',
        'products_loaded': len(processed_products),
        'dynamodb_count': dynamodb_count,
        'opensearch_count': opensearch_count,
        'status': 'success'
    }

def load_catalog() -> List[Dict[str, Any]]:
    """Load the product catalog from embedded data"""
    # Embedded product catalog
    return [
        {
            "id": "1",
            "name": "Multivitamin Complex",
            "description": "Complete daily multivitamin with essential vitamins and minerals for overall health support",
            "category": "Vitamins & Supplements",
            "price": 24.99,
            "image_url": "/assets/vitamin-stock.png"
        },
        {
            "id": "2", 
            "name": "Omega-3 Fish Oil",
            "description": "High-quality fish oil supplement rich in EPA and DHA for heart and brain health",
            "category": "Vitamins & Supplements",
            "price": 32.99,
            "image_url": "/assets/vitamin-stock.png"
        },
        {
            "id": "3",
            "name": "Vitamin D3 2000 IU",
            "description": "High-potency vitamin D3 supplement for bone health and immune system support",
            "category": "Vitamins & Supplements", 
            "price": 18.99,
            "image_url": "/assets/vitamin-stock.png"
        },
        {
            "id": "4",
            "name": "Probiotics 50 Billion CFU",
            "description": "Advanced probiotic formula with 50 billion CFU for digestive and immune health",
            "category": "Vitamins & Supplements",
            "price": 39.99,
            "image_url": "/assets/vitamin-stock.png"
        },
        {
            "id": "5",
            "name": "Magnesium Glycinate 400mg",
            "description": "Highly bioavailable magnesium supplement for muscle relaxation and sleep support",
            "category": "Vitamins & Supplements",
            "price": 22.99,
            "image_url": "/assets/vitamin-stock.png"
        }
        # Add more products as needed - truncated for brevity
    ]

def generate_embedding(bedrock_client, text: str, model_id: str) -> List[float]:
    """Generate embedding using AWS Bedrock"""
    try:
        body = json.dumps({
            "inputText": text,
            "dimensions": 1024,
            "normalize": True
        })
        
        response = bedrock_client.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',  # Use Titan for embeddings
            body=body,
            contentType='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        return response_body.get('embedding', [])
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        # Return a zero vector as fallback
        return [0.0] * 1024

def load_to_dynamodb(products: List[Dict[str, Any]], table_name: str, region: str) -> int:
    """Load products to DynamoDB"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)
        
        count = 0
        with table.batch_writer() as batch:
            for product in products:
                # Remove embedding for DynamoDB (too large)
                dynamo_product = {k: v for k, v in product.items() if k != 'embedding'}
                batch.put_item(Item=dynamo_product)
                count += 1
                
        return count
        
    except Exception as e:
        logger.error(f"Error loading to DynamoDB: {e}")
        return 0

def load_to_opensearch(products: List[Dict[str, Any]], endpoint: str, index_name: str, region: str) -> int:
    """Load products to OpenSearch"""
    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from requests_aws4auth import AWS4Auth
        
        # Parse the endpoint to get the host
        if endpoint.startswith('https://'):
            host = endpoint.replace('https://', '')
        elif endpoint.startswith('http://'):
            host = endpoint.replace('http://', '')
        else:
            host = endpoint
            
        # Remove any trailing slashes or paths
        host = host.split('/')[0]
        
        logger.info(f"Connecting to OpenSearch host: {host} in region: {region}")
        
        # Create AWS4Auth for OpenSearch - use 'es' service for compatibility
        credentials = boto3.Session().get_credentials()
        if not credentials:
            raise Exception("Unable to get AWS credentials")
            
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'es',  # Use 'es' service name for OpenSearch compatibility
            session_token=credentials.token
        )
        
        # Create OpenSearch client
        client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=60,
            max_retries=3,
            retry_on_timeout=True
        )
        
        # Test the connection
        try:
            info = client.info()
            logger.info(f"Connected to OpenSearch: {info.get('version', {}).get('number', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to connect to OpenSearch: {e}")
            raise
        
        # Create index if it doesn't exist
        index_body = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 2,
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 24
                            }
                        }
                    },
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "category": {"type": "keyword"},
                    "price": {"type": "float"}
                }
            }
        }
        
        if not client.indices.exists(index=index_name):
            client.indices.create(index=index_name, body=index_body)
            logger.info(f"Created OpenSearch index: {index_name}")
        
        # Bulk load products
        actions = []
        for product in products:
            action = {
                "_index": index_name,
                "_id": product["id"],
                "_source": product
            }
            actions.append(action)
        
        if actions:
            from opensearchpy.helpers import bulk
            bulk(client, actions)
            logger.info(f"Bulk loaded {len(actions)} products to OpenSearch")
            
        return len(actions)
        
    except Exception as e:
        logger.error(f"Error loading to OpenSearch: {e}")
        return 0
