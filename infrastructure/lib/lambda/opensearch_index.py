# import os
# import json
# import boto3
# from opensearchpy import OpenSearch, RequestsHttpConnection
# from requests_aws4auth import AWS4Auth

# # Get configuration from environment variables
# REGION = os.environ['AWS_REGION']
# SERVICE = 'es'  # The service name for OpenSearch/Elasticsearch is 'es'

# def get_opensearch_client(domain_endpoint: str) -> OpenSearch:
#     """Initializes and returns an OpenSearch client with SigV4 auth."""
#     credentials = boto3.Session().get_credentials()
#     aws_auth = AWS4Auth(
#         credentials.access_key,
#         credentials.secret_key,
#         REGION,
#         SERVICE,
#         session_token=credentials.token
#     )
    
#     client = OpenSearch(
#         hosts=[{'host': domain_endpoint, 'port': 443}],
#         http_auth=aws_auth,
#         use_ssl=True,
#         verify_certs=True,
#         connection_class=RequestsHttpConnection,
#         pool_maxsize=20
#     )
#     return client

# def handler(event, context):
#     """
#     Lambda handler for the OpenSearch index custom resource.
#     Manages an OpenSearch index based on CloudFormation events (Create, Update, Delete).
#     """
#     print(f"Received event: {json.dumps(event)}")
    
#     props = event['ResourceProperties']
#     domain_endpoint = props['DOMAIN_ENDPOINT']
#     index_name = props['INDEX_NAME']
#     index_body = props['INDEX_BODY']  # This will be a dictionary
    
#     # Ensure numeric parameters in KNN vector field are integers
#     if 'mappings' in index_body and 'properties' in index_body['mappings']:
#         for field_name, field_config in index_body['mappings']['properties'].items():
#             if field_config.get('type') == 'knn_vector' and 'method' in field_config:
#                 method = field_config['method']
#                 if 'parameters' in method:
#                     params = method['parameters']
#                     # Convert string numbers to integers
#                     for param_name, param_value in params.items():
#                         if isinstance(param_value, str) and param_value.isdigit():
#                             params[param_name] = int(param_value)
#                         elif isinstance(param_value, (int, float)):
#                             params[param_name] = int(param_value)
    
#     print(f"Processed index body: {json.dumps(index_body, indent=2)}")
    
#     client = get_opensearch_client(domain_endpoint)
    
#     try:
#         request_type = event['RequestType']
        
#         if request_type in ['Create', 'Update']:
#             print(f"Request type is {request_type}. Checking for index '{index_name}'.")
            
#             if client.indices.exists(index=index_name):
#                 print(f"Index '{index_name}' already exists. No action taken on update.")
#                 # In a real-world update, you might apply new settings/mappings here
#             else:
#                 print(f"Creating index '{index_name}' with body: {json.dumps(index_body, indent=2)}")
#                 client.indices.create(index=index_name, body=index_body)
#                 print(f"Successfully created index '{index_name}'.")

#         elif request_type == 'Delete':
#             print(f"Request type is Delete. Deleting index '{index_name}'.")
#             # ignore=[404] prevents an error if the index is already gone
#             client.indices.delete(index=index_name, ignore=[404])
#             print(f"Successfully deleted index '{index_name}' (if it existed).")

#     except Exception as e:
#         print(f"Failed to manage index '{index_name}': {e}")
#         # Re-raising the exception is critical to signal failure to CloudFormation
#         raise
        
#     return {'PhysicalResourceId': index_name}
