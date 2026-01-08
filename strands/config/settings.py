import os
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        # Load AWS resource configuration from SSM parameter if available
        self._aws_resources = {}
        aws_resource_param = os.getenv('AWS_RESOURCE_NAMES_PARAMETER')
        if aws_resource_param:
            try:
                self._aws_resources = json.loads(aws_resource_param)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Warning: Failed to parse AWS_RESOURCE_NAMES_PARAMETER: {e}")
                self._aws_resources = {}

    @property
    def AWS_REGION(self) -> str:
        return os.getenv('AWS_REGION', 'us-east-1')

    @property
    def DYNAMODB_CUSTOMERS_TABLE(self) -> str:
        return os.getenv('DYNAMODB_CUSTOMERS_TABLE', 'customers')
    
    @property
    def DYNAMODB_PRODUCTS_TABLE(self) -> str:
        return os.getenv('DYNAMODB_PRODUCTS_TABLE', 'products')
    
    @property
    def DYNAMODB_SEARCH_HISTORY_TABLE(self) -> str:
        return os.getenv('DYNAMODB_SEARCH_HISTORY_TABLE', 'search_history')

    @property
    def DYNAMODB_ORDERS_TABLE(self) -> str:
        return os.getenv('DYNAMODB_ORDERS_TABLE', 'orders')

    @property
    def OPENSEARCH_ENDPOINT(self) -> Optional[str]:
        # First try environment variable, then SSM parameter
        endpoint = os.getenv('OPENSEARCH_ENDPOINT')
        if not endpoint and self._aws_resources:
            endpoint = self._aws_resources.get('OPENSEARCH_ENDPOINT')
        return endpoint
    
    @property
    def OPENSEARCH_INDEX_NAME(self) -> str:
        return os.getenv('OPENSEARCH_INDEX_NAME', 'products')

    @property
    def BEDROCK_MODEL_ID(self) -> str:
        return os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0')

    @property
    def DEBUG(self) -> bool:
        return os.getenv('DEBUG', 'False').lower() == 'true'
    
    @property
    def PORT(self) -> int:
        return int(os.getenv('PORT', 8000))

    @property
    def CORS_ORIGINS(self) -> list:
        return os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')

settings = Settings()

def get_settings() -> Settings:
    """Get settings instance for dependency injection."""
    return settings
