import boto3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from config.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

class OpenSearchService:
    """OpenSearch service for semantic search and indexing using managed domains"""
    
    def __init__(self):
        """Initialize OpenSearch client for managed domain"""
        # Initialize clients as None first
        self.client = None
        self.os_client = None
        self._session = None
        
        try:
            self.region = settings.AWS_REGION
            self.domain_endpoint = settings.OPENSEARCH_ENDPOINT
            self.index_name = settings.OPENSEARCH_INDEX_NAME
            
            # Validate required settings
            if not self.domain_endpoint:
                logger.warning("OpenSearch domain endpoint not configured")
                return
                
            if not self.index_name:
                logger.warning("OpenSearch index name not configured")
                return
            
            # Initialize persistent session for credential management
            self._initialize_client()
            
            logger.info("OpenSearch service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch service: {str(e)}")
            self.client = None
            self.os_client = None

    def _initialize_client(self):
        """Initialize or refresh OpenSearch client with current credentials"""
        try:
            # Create a new session to get fresh credentials
            self._session = boto3.Session()
            credentials = self._session.get_credentials()
            
            if not credentials:
                logger.error("AWS credentials not available")
                return False
                
            # Initialize OpenSearch client for data operations
            service = 'es'  # Use 'es' for managed domains
            
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region,
                service,
                session_token=credentials.token
            )
            
            # Extract host from endpoint (remove https://)
            host = self.domain_endpoint.replace("https://", "").replace("http://", "")
            
            # Build the OpenSearch client for managed domain with increased timeouts for VPC
            self.os_client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=300,  # Increased to 5 minutes for VPC connections
                max_retries=5,  # More retries for VPC connectivity
                retry_on_timeout=True,
                # Additional connection settings for VPC
                http_compress=True,
                headers={'Connection': 'keep-alive'},
                # Connection pool settings
                maxsize=25,
                block=True
            )
            
            # Set client to the same as os_client for backward compatibility
            self.client = self.os_client
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {str(e)}")
            return False

    def _refresh_credentials_if_needed(self):
        """Check if credentials need refresh and reinitialize client if necessary"""
        try:
            if not self._session:
                logger.info("No session found, initializing client")
                return self._initialize_client()
            
            # Get current credentials
            credentials = self._session.get_credentials()
            
            if not credentials:
                logger.warning("No credentials available, reinitializing client")
                return self._initialize_client()
            
            # Check if credentials are expired or about to expire
            if hasattr(credentials, '_expiry_time') and credentials._expiry_time:
                from datetime import datetime, timezone
                import time
                
                # If credentials expire within 5 minutes, refresh them
                current_time = datetime.now(timezone.utc)
                if credentials._expiry_time <= current_time.timestamp() + 300:
                    logger.info("Credentials expiring soon, refreshing client")
                    return self._initialize_client()
            
            return True
            
        except Exception as e:
            logger.warning(f"Error checking credential expiry, reinitializing: {str(e)}")
            return self._initialize_client()

    def _ensure_client(self):
        """Ensure OpenSearch clients are available and credentials are fresh"""
        # First check if credentials need refresh
        if not self._refresh_credentials_if_needed():
            raise ValueError("Failed to refresh AWS credentials")
            
        if not self.client or not self.os_client:
            raise ValueError("OpenSearch clients not initialized. Check configuration.")

    async def get_cluster_settings(self) -> Dict[str, Any]:
        """Get current cluster settings to validate configuration"""
        self._ensure_client()
        
        try:
            # Get cluster settings
            persistent_settings = self.os_client.cluster.get_settings(
                include_defaults=True,
                flat_settings=True
            )
            
            return {
                "persistent": persistent_settings.get("persistent", {}),
                "transient": persistent_settings.get("transient", {}),
                "defaults": persistent_settings.get("defaults", {})
            }
            
        except Exception as e:
            logger.error(f"Failed to get cluster settings: {str(e)}")
            raise

    async def update_cluster_settings(self) -> Dict[str, Any]:
        """Update cluster settings to match the specified configuration"""
        self._ensure_client()
        
        try:
            # Settings that match the cluster configuration requirements
            cluster_settings = {
                "persistent": {
                    # Field data cache allocation (20% as specified)
                    "indices.fielddata.cache.size": "20%",
                    # Max clause count (1024 as specified)
                    "indices.query.bool.max_clause_count": 1024,
                    # Allow references to indexes inside HTTP request bodies
                    "rest.action.multi.allow_explicit_index": True,
                    # Optimize for 3-node cluster performance
                    "cluster.routing.allocation.awareness.attributes": "zone",
                    "cluster.routing.allocation.awareness.force.zone.values": "us-east-1a,us-east-1b,us-east-1c",
                    # Snapshot settings (hourly as specified)
                    "cluster.routing.allocation.disk.threshold_enabled": True,
                    "cluster.routing.allocation.disk.watermark.low": "85%",
                    "cluster.routing.allocation.disk.watermark.high": "90%",
                    "cluster.routing.allocation.disk.watermark.flood_stage": "95%"
                }
            }
            
            # Apply the settings
            response = self.os_client.cluster.put_settings(body=cluster_settings)
            
            logger.info("Cluster settings updated successfully for 3-node configuration")
            return {
                "success": True,
                "message": "Cluster settings updated for optimal 3-node performance",
                "applied_settings": cluster_settings["persistent"]
            }
            
        except Exception as e:
            logger.error(f"Failed to update cluster settings: {str(e)}")
            raise

    async def delete_index(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """Delete OpenSearch index"""
        self._ensure_client()
        
        if not index_name:
            index_name = self.index_name
        
        try:
            # Check if index exists
            if self.os_client.indices.exists(index=index_name):
                response = self.os_client.indices.delete(index=index_name)
                logger.info(f"Index {index_name} deleted successfully")
                return {"message": f"Index {index_name} deleted successfully", "deleted": True}
            else:
                logger.info(f"Index {index_name} does not exist")
                return {"message": f"Index {index_name} does not exist", "deleted": False}
                
        except Exception as e:
            logger.error(f"Failed to delete index {index_name}: {str(e)}")
            raise

    async def create_index(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """Create OpenSearch index with proper mappings for products"""
        self._ensure_client()
        
        if not index_name:
            index_name = self.index_name
        
        try:
            mapping = {
                "settings": {
                    "index": {
                        # Optimized for 3-node cluster with 3-AZ deployment
                        "number_of_shards": 1,  # One shard for simplicity
                        "number_of_replicas": 2,  # Two replicas to satisfy zone awareness requirement (1 primary + 2 replicas = 3 total copies = multiple of 3)
                        "knn": True,
                        "knn.algo_param.ef_search": 100,
                        # Advanced cluster settings matching configuration
                        "max_terms_count": 1024,  # Match cluster max terms count setting
                        "requests.cache.enable": True,
                        "refresh_interval": "1s",  # Optimize for search performance
                        "translog.durability": "request",  # Ensure data durability
                        "translog.sync_interval": "5s"
                    },
                    "analysis": {
                        "analyzer": {
                            "custom_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "stop", "snowball"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "product_id": {"type": "keyword"},
                        "name": {
                            "type": "text",
                            "analyzer": "custom_analyzer",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "category": {
                            "type": "text",
                            "analyzer": "custom_analyzer",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "brand": {
                            "type": "text",
                            "analyzer": "custom_analyzer",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "price": {"type": "float"},
                        "description": {
                            "type": "text",
                            "analyzer": "custom_analyzer"
                        },
                        "ingredients": {
                            "type": "text",
                            "analyzer": "custom_analyzer"
                        },
                        "benefits": {
                            "type": "text",
                            "analyzer": "custom_analyzer"
                        },
                        "rating": {"type": "float"},
                        "servings_per_container": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "serving_size": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "directions": {
                            "type": "text",
                            "analyzer": "custom_analyzer"
                        },
                        "warnings": {
                            "type": "text",
                            "analyzer": "custom_analyzer"
                        },
                        "certifications": {
                            "type": "text",
                            "analyzer": "custom_analyzer"
                        },
                        "dimensions": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "weight": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "volume": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword"}}
                        },
                        "stock_status": {
                            "type": "keyword"
                        },
                        "in_stock": {
                            "type": "boolean"
                        },
                        "reviews_count": {"type": "long"},
                        "indexed_at": {"type": "date"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 1024,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 256,
                                    "m": 32
                                }
                            }
                        }
                    }
                }
            }
            
            # Check if index already exists
            try:
                if self.os_client.indices.exists(index=index_name):
                    logger.warning(f"Index {index_name} already exists. Deleting and recreating with updated mapping.")
                    # Delete the existing index to recreate with proper mapping
                    await self.delete_index(index_name)
            except Exception:
                pass
            
            # Create the index
            response = self.os_client.indices.create(index=index_name, body=mapping)
            
            logger.info(f"Index {index_name} created successfully")
            return {"message": f"Index {index_name} created successfully", "created": True}
            
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {str(e)}")
            raise

    async def bulk_index_products(self, products: List[Dict[str, Any]], index_name: Optional[str] = None) -> Dict[str, Any]:
        """Bulk index multiple products"""
        self._ensure_client()
        
        if not index_name:
            index_name = self.index_name
        
        try:
            # Prepare bulk actions in the correct format for OpenSearch
            actions = []
            
            for product in products:
                # Create a copy of the product to avoid modifying the original
                product_copy = product.copy()
                product_copy['indexed_at'] = datetime.now().isoformat()
                
                # Ensure embedding is present and has correct dimension
                if 'embedding' not in product_copy or not product_copy['embedding']:
                    logger.warning(f"Product {product_copy.get('id')} missing embedding, using zero vector")
                    product_copy['embedding'] = [0.0] * 1024
                elif len(product_copy['embedding']) != 1024:
                    logger.warning(f"Product {product_copy.get('id')} has incorrect embedding dimension: {len(product_copy['embedding'])}")
                    if len(product_copy['embedding']) > 1024:
                        product_copy['embedding'] = product_copy['embedding'][:1024]
                    else:
                        product_copy['embedding'].extend([0.0] * (1024 - len(product_copy['embedding'])))
                
                # Create the action document for bulk indexing in correct format
                action = {
                    "_index": index_name,
                    "_id": product_copy['id'],
                    "_source": product_copy  # Document data should be in _source
                }
                actions.append(action)
            
            # Use OpenSearch client's bulk helper
            from opensearchpy.helpers import bulk, BulkIndexError
            
            # Execute bulk indexing with optimizations for 3-node cluster
            try:
                successful, failed = bulk(
                    self.os_client,
                    actions,
                    chunk_size=150,  # Increased for better throughput with 3 nodes
                    request_timeout=600,  # Longer timeout for large batches
                    max_retries=5,  # More retries for distributed setup
                    initial_backoff=2,
                    max_backoff=600,
                    raise_on_error=False,  # Don't raise on individual document errors
                    raise_on_exception=True  # Raise on connection/client errors
                )
                
                failed_count = len(failed) if isinstance(failed, list) else 0
                
                logger.info(f"Bulk indexed {successful} products successfully, {failed_count} failed")
                
                return {
                    "success": True,
                    "total_products": len(products),
                    "successful": successful,
                    "failed": failed_count,
                    "errors": failed[:10] if isinstance(failed, list) and failed else []
                }
                
            except BulkIndexError as e:
                # Handle bulk indexing errors
                failed_docs = []
                successful_count = 0
                
                for error in e.errors:
                    failed_docs.append({
                        "id": error.get("index", {}).get("_id", "unknown"),
                        "error": error.get("index", {}).get("error", {}).get("reason", str(error))
                    })
                
                # Calculate successful count
                successful_count = len(products) - len(failed_docs)
                
                logger.warning(f"Bulk indexing completed with errors: {successful_count} successful, {len(failed_docs)} failed")
                
                return {
                    "success": successful_count > 0,
                    "total_products": len(products),
                    "successful": successful_count,
                    "failed": len(failed_docs),
                    "errors": failed_docs[:10]
                }
            
        except Exception as e:
            logger.error(f"Failed to bulk index products: {str(e)}")
            raise

    async def simple_search(self, 
                           query: str,
                           size: int = 10) -> Dict[str, Any]:
        """Perform the simplest possible search query for basic functionality"""
        self._ensure_client()
        
        try:
            # Simple match query - most basic OpenSearch query
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["name", "brand", "ingredients"]
                    }
                },
                "size": size,
                "_source": {
                    "excludes": ["embedding"]
                }
            }
            
            start_time = datetime.now()
            response = self.os_client.search(
                index=self.index_name,
                body=search_body
            )
            end_time = datetime.now()
            
            hits = response['hits']
            results = []
            
            for hit in hits['hits']:
                result = hit['_source']
                result['_score'] = hit['_score']
                results.append(result)
            
            took_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.info(f"Simple search completed: {hits['total']['value']} results in {took_ms:.2f}ms")
            
            return {
                "query": query,
                "total_hits": hits['total']['value'],
                "results": results,
                "took_ms": took_ms,
                "max_score": hits.get('max_score', 0)
            }
            
        except Exception as e:
            logger.error(f"Simple search failed for query '{query}': {str(e)}")
            raise

    async def search_products(self, 
                            query: str,
                            filters: Optional[Dict[str, Any]] = None,
                            size: int = 10,
                            from_: int = 0,
                            sort_by: Optional[str] = None) -> Dict[str, Any]:
        """Search products using keyword search with enhanced scoring"""
        self._ensure_client()
        
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "name^4",
                                        "ingredients^1.5",
                                        "category^2",
                                        "brand^2"
                                    ],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                    "operator": "or",
                                    "minimum_should_match": "80%"
                                }
                            }
                        ],
                        "should": [
                            {
                                "match_phrase": {
                                    "name": {
                                        "query": query,
                                        "boost": 2
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": size,
                "from": from_,
                "_source": {
                    "excludes": ["embedding"]  # Exclude embedding from results
                }
            }
            
            # Add filters
            if filters:
                filter_clauses = []
                
                if filters.get('category'):
                    filter_clauses.append({
                        "term": {"category.keyword": filters['category']}
                    })
                
                if filters.get('brand'):
                    filter_clauses.append({
                        "term": {"brand.keyword": filters['brand']}
                    })
                
                if filters.get('price_min') or filters.get('price_max'):
                    price_range = {}
                    if filters.get('price_min'):
                        price_range['gte'] = filters['price_min']
                    if filters.get('price_max'):
                        price_range['lte'] = filters['price_max']
                    
                    filter_clauses.append({
                        "range": {"price": price_range}
                    })
                
                if filters.get('rating_min'):
                    filter_clauses.append({
                        "range": {"rating": {"gte": filters['rating_min']}}
                    })
                
                if filter_clauses:
                    search_body["query"]["bool"]["filter"] = filter_clauses
            
            # Add sorting
            if sort_by:
                if sort_by == 'price_asc':
                    search_body["sort"] = [{"price": {"order": "asc"}}, "_score"]
                elif sort_by == 'price_desc':
                    search_body["sort"] = [{"price": {"order": "desc"}}, "_score"]
                elif sort_by == 'rating':
                    search_body["sort"] = [{"rating": {"order": "desc"}}, "_score"]
                elif sort_by == 'name':
                    search_body["sort"] = [{"name.keyword": {"order": "asc"}}, "_score"]
            
            start_time = datetime.now()
            response = self.os_client.search(
                index=self.index_name,
                body=search_body
            )
            end_time = datetime.now()
            
            hits = response['hits']
            results = []
            
            for hit in hits['hits']:
                result = hit['_source']
                result['_score'] = hit['_score']
                results.append(result)
            
            took_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.info(f"Search completed: {hits['total']['value']} results in {took_ms:.2f}ms")
            
            return {
                "query": query,
                "total_hits": hits['total']['value'],
                "results": results,
                "from": from_,
                "size": size,
                "took_ms": took_ms,
                "max_score": hits.get('max_score', 0)
            }
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            raise

    async def semantic_search(self, 
                            query_embedding: List[float],
                            filters: Optional[Dict[str, Any]] = None,
                            size: int = 10,
                            similarity_threshold: float = 0.0) -> Dict[str, Any]:
        """Perform semantic search using vector embeddings with enhanced filtering"""
        self._ensure_client()
        
        try:
            # Validate embedding dimension
            if len(query_embedding) != 1024:
                raise ValueError(f"Expected embedding dimension 1024, got {len(query_embedding)}")
            
            # Optimized KNN search for 3-node cluster configuration
            search_body = {
                "size": max(size * 3, 50),  # Get more results to ensure we have enough after filtering
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": query_embedding,
                            "k": max(size * 3, 50)
                        }
                    }
                },
                "_source": {
                    "excludes": ["embedding"]  # Exclude embedding from results
                }
            }
            
            # Add filters by wrapping KNN in a bool query when filters are present
            if filters:
                filter_clauses = []
                
                if filters.get('category'):
                    filter_clauses.append({
                        "term": {"category.keyword": filters['category']}
                    })
                
                if filters.get('brand'):
                    filter_clauses.append({
                        "term": {"brand.keyword": filters['brand']}
                    })
                
                if filters.get('price_min') or filters.get('price_max'):
                    price_range = {}
                    if filters.get('price_min'):
                        price_range['gte'] = filters['price_min']
                    if filters.get('price_max'):
                        price_range['lte'] = filters['price_max']
                    
                    filter_clauses.append({
                        "range": {"price": price_range}
                    })
                
                if filters.get('rating_min'):
                    filter_clauses.append({
                        "range": {"rating": {"gte": filters['rating_min']}}
                    })
                
                if filter_clauses:
                    # Wrap the KNN query in a bool query to apply filters
                    knn_query = search_body["query"]
                    search_body["query"] = {
                        "bool": {
                            "must": [knn_query],
                            "filter": filter_clauses
                        }
                    }
            
            start_time = datetime.now()
            response = self.os_client.search(
                index=self.index_name,
                body=search_body
            )
            end_time = datetime.now()
            
            hits = response['hits']
            results = []
            
            # Process all results and calculate proper similarity scores
            all_scores = [hit['_score'] for hit in hits['hits']] if hits['hits'] else []
            max_score = max(all_scores) if all_scores else 0
            min_score = min(all_scores) if all_scores else 0
            
            # Log score distribution for debugging
            logger.info(f"Score range: {min_score:.4f} - {max_score:.4f}, Total hits: {len(hits['hits'])}")
            
            for hit in hits['hits']:
                raw_score = hit['_score']
                
                # For cosine similarity in OpenSearch, higher scores are better
                # Convert to a normalized similarity score (0-1 range)
                if max_score > min_score:
                    normalized_similarity = (raw_score - min_score) / (max_score - min_score)
                else:
                    normalized_similarity = 1.0 if raw_score > 0 else 0.0
                
                # Apply similarity threshold to normalized score
                if normalized_similarity >= similarity_threshold:
                    result = hit['_source']
                    result['_score'] = raw_score
                    result['similarity'] = normalized_similarity
                    result['raw_score'] = raw_score
                    results.append(result)
            
            # Limit to requested size
            results = results[:size]
            
            took_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.info(f"Semantic search completed: {len(results)}/{len(hits['hits'])} results in {took_ms:.2f}ms (threshold: {similarity_threshold})")
            
            return {
                "total_hits": len(results),
                "total_candidates": len(hits['hits']),
                "results": results,
                "similarity_threshold": similarity_threshold,
                "took_ms": took_ms,
                "max_score": max_score,
                "score_range": {"min": min_score, "max": max_score}
            }
            
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, str]:
        """Check OpenSearch service health with comprehensive diagnostics"""
        try:
            # Check if clients are initialized
            if not self.os_client:
                return {
                    'status': 'unhealthy', 
                    'message': 'OpenSearch clients not initialized',
                    'details': {
                        'domain_endpoint': getattr(self, 'domain_endpoint', 'Not configured'),
                        'index_name': getattr(self, 'index_name', 'Not configured'),
                        'region': getattr(self, 'region', 'Not configured')
                    }
                }
            
            # Test actual connectivity to OpenSearch
            try:
                # Check if we can ping the cluster
                ping_response = self.os_client.ping()
                if not ping_response:
                    return {
                        'status': 'unhealthy',
                        'message': 'OpenSearch cluster is not responding to ping',
                        'details': {
                            'domain_endpoint': self.domain_endpoint,
                            'ping_response': False
                        }
                    }
                
                # Check cluster health
                cluster_health = self.os_client.cluster.health()
                cluster_status = cluster_health.get('status', 'unknown')
                
                # Check if index exists
                index_exists = self.os_client.indices.exists(index=self.index_name)
                
                if cluster_status in ['green', 'yellow']:
                    return {
                        'status': 'healthy',
                        'message': 'OpenSearch service is operational',
                        'cluster_status': cluster_status,
                        'number_of_nodes': cluster_health.get('number_of_nodes', 0),
                        'active_shards': cluster_health.get('active_shards', 0),
                        'index_exists': index_exists,
                        'cluster_name': cluster_health.get('cluster_name', 'unknown')
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'message': f'OpenSearch cluster status is {cluster_status}',
                        'cluster_status': cluster_status,
                        'index_exists': index_exists,
                        'details': cluster_health
                    }
                    
            except Exception as conn_error:
                return {
                    'status': 'unhealthy',
                    'message': f'Failed to connect to OpenSearch: {str(conn_error)}',
                    'details': {
                        'domain_endpoint': self.domain_endpoint,
                        'error_type': type(conn_error).__name__,
                        'error_details': str(conn_error)
                    }
                }
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': f'Health check error: {str(e)}',
                'details': {
                    'error_type': type(e).__name__
                }
            }

# Singleton instance
opensearch_service = OpenSearchService()
