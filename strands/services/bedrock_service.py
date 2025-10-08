import boto3
import json
import logging
from typing import List, Dict, Any

from config.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

class BedrockService:
    """Service for Amazon Bedrock AI operations including embeddings and LLM calls"""
    
    def __init__(self):
        """Initialize Bedrock client"""
        try:
            self.region = settings.AWS_REGION
            self.bedrock_runtime = boto3.client(
                'bedrock-runtime',
                region_name=self.region
            )
            
            # Default models
            self.embedding_model_id = "amazon.titan-embed-text-v2:0"
            # Use Claude model from settings
            self.llm_model_id = settings.BEDROCK_MODEL_ID
            
            logger.info("Bedrock service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock service: {str(e)}")
            self.bedrock_runtime = None

    def _ensure_client(self):
        """Ensure Bedrock client is available"""
        if not self.bedrock_runtime:
            raise ValueError("Bedrock client not initialized. Check AWS credentials and region.")

    async def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for the given text using Amazon Titan Embeddings
        
        Args:
            text: Text to generate embeddings for
            
        Returns:
            List of floats representing the embedding vector (1024 dimensions)
        """
        self._ensure_client()
        
        try:
            # Clean and prepare text
            cleaned_text = text.strip()
            if not cleaned_text:
                logger.warning("Empty text provided for embedding generation")
                return [0.0] * 1024  # Return zero vector for empty text
            
            # Truncate text if too long (Titan has a limit)
            if len(cleaned_text) > 8000:
                cleaned_text = cleaned_text[:8000]
                logger.warning(f"Text truncated to 8000 characters for embedding generation")
            
            # Prepare request body for Titan Embeddings
            body = {
                "inputText": cleaned_text
            }
            
            # Call Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.embedding_model_id,
                body=json.dumps(body),
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding', [])
            
            if not embedding:
                logger.error("No embedding returned from Bedrock")
                return [0.0] * 1024
            
            # Ensure we have the correct dimension (1024)
            if len(embedding) != 1024:
                logger.warning(f"Expected 1024 dimensions, got {len(embedding)}. Padding or truncating.")
                if len(embedding) > 1024:
                    embedding = embedding[:1024]
                else:
                    embedding.extend([0.0] * (1024 - len(embedding)))
            
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            # Return zero vector as fallback
            return [0.0] * 1024

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for i, text in enumerate(texts):
            try:
                embedding = await self.generate_embeddings(text)
                embeddings.append(embedding)
                
                # Log progress for large batches
                if (i + 1) % 10 == 0:
                    logger.info(f"Generated embeddings for {i + 1}/{len(texts)} texts")
                    
            except Exception as e:
                logger.error(f"Failed to generate embedding for text {i}: {str(e)}")
                embeddings.append([0.0] * 1024)  # Fallback zero vector
        
        logger.info(f"Generated embeddings for {len(embeddings)} texts")
        return embeddings

    async def generate_product_recommendations(self, 
                                            customer_profile: Dict[str, Any],
                                            available_products: List[Dict[str, Any]],
                                            max_recommendations: int = 10) -> Dict[str, Any]:
        """
        Generate personalized product recommendations using LLM
        
        Args:
            customer_profile: Customer information and preferences
            available_products: Products to choose from
            max_recommendations: Maximum number of recommendations
            
        Returns:
            Personalized recommendations with explanations
        """
        self._ensure_client()
        
        try:
            # Prepare customer context
            customer_summary = {
                "age": customer_profile.get('age'),
                "health_conditions": customer_profile.get('health_conditions', []),
                "preferences": customer_profile.get('preferences', {}),
                "previous_purchases": customer_profile.get('purchase_history', [])[-5:] if customer_profile.get('purchase_history') else []
            }
            
            # Prepare product context (limit to prevent token overflow)
            products_summary = []
            for product in available_products[:20]:  # Limit to 20 products
                summary = {
                    "id": product.get('id'),
                    "name": product.get('name'),
                    "category": product.get('category'),
                    "price": product.get('price'),
                    "benefits": product.get('benefits', [])[:3],  # Top 3 benefits
                    "rating": product.get('rating')
                }
                products_summary.append(summary)
            
            # Create recommendation prompt
            prompt = f"""
            Human: Generate personalized product recommendations for this customer:

            Customer Profile:
            {json.dumps(customer_summary, indent=2)}

            Available Products:
            {json.dumps(products_summary, indent=2)}

            Please recommend up to {max_recommendations} products that would be most suitable for this customer. For each recommendation, provide:
            1. Product ID and name
            2. Why it's suitable for this customer
            3. Confidence score (1-10)

            Format your response as JSON with this structure:
            {{
                "recommendations": [
                    {{
                        "product_id": "...",
                        "product_name": "...",
                        "reason": "...",
                        "confidence_score": 8
                    }}
                ],
                "summary": "Brief explanation of recommendation strategy"
            }}

            Assistant: """
            
            # Call Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.llm_model_id,
                body=json.dumps(body),
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            recommendations_text = response_body.get('content', [{}])[0].get('text', '{}')
            
            # Try to parse JSON response
            try:
                recommendations_data = json.loads(recommendations_text)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                recommendations_data = {
                    "recommendations": [],
                    "summary": "Unable to parse recommendations",
                    "raw_response": recommendations_text
                }
            
            return recommendations_data
            
        except Exception as e:
            logger.error(f"Failed to generate product recommendations: {str(e)}")
            return {
                "recommendations": [],
                "error": str(e),
                "summary": "Unable to generate recommendations at this time"
            }

    async def health_check(self) -> Dict[str, str]:
        """Check Bedrock service health"""
        if not self.bedrock_runtime:
            return {'status': 'unhealthy', 'message': 'Bedrock client not initialized'}
        
        try:
            # Test with a simple embedding generation
            test_embedding = await self.generate_embeddings("health check")
            
            if len(test_embedding) == 1024:
                return {
                    'status': 'healthy',
                    'message': 'Bedrock service is working correctly',
                    'embedding_model': self.embedding_model_id
                }
            else:
                return {
                    'status': 'unhealthy', 
                    'message': f'Unexpected embedding dimension: {len(test_embedding)}'
                }
                
        except Exception as e:
            logger.error(f"Bedrock health check failed: {str(e)}")
            return {'status': 'unhealthy', 'message': str(e)}

# Singleton instance
bedrock_service = BedrockService()
