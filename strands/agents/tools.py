from strands import tool
from utils.catalog_loader import catalog_loader
from services.dynamodb_service import dynamodb_service

@tool
async def search_products(query: str, search_type: str = "keyword"):
  """
  Search for healthcare products using keyword or semantic search.
  
  Args:
      query (str): The search query string. Can be product names, descriptions, 
                  ingredients, benefits, categories, brands, or any combination.
                  Examples: "vitamin D supplements", "pain relief cream", 
                  "organic skincare", "first aid supplies"
      search_type (str, optional): The type of search to perform. Defaults to "keyword".
        - "keyword": Traditional text-based search using OpenSearch 
          with fuzzy matching, phrase matching, and field boosting.
          Best for exact product names, brands, or categories.
        - "semantic": AI-powered semantic search using embeddings. Better for conceptual queries, finding similar products, or natural language descriptions.

  Returns:
      List[Dict[str, Any]]: A list of matching product dictionaries. Each product contains:
          - id (str): Unique product identifier
          - name (str): Product name
          - description (str): Product description
          - category (str): Product category (e.g., "Vitamins", "Skincare", "First Aid")
          - brand (str): Product brand name
          - price (float): Product price
          - rating (float): Average customer rating
          - ingredients (List[str]): List of product ingredients
          - benefits (List[str]): List of product benefits
          - certifications (List[str]): Product certifications (e.g., "Organic", "FDA Approved")
          - stock_status (str): Current stock availability
          - _score (float): Search relevance score (higher = more relevant)
          - Additional fields may include: serving_size, directions, warnings, etc.
  """
  print(f'search query - {query}')
  results = await catalog_loader.search_products_by_query(query=query, search_type=search_type)
  return results.get('results', [])

@tool
async def get_customer_data(customer_id: str):
  """
  Fetch customer data from DynamoDB by customer ID.
  
  Args:
      customer_id (str): The unique identifier for the customer
      
  Returns:
      Dict[str, Any]: Customer data dictionary containing:
          - customer_id (str): Unique customer identifier
          - personal_info (Dict): Personal information including name, age, email, address
          - health_profile (Dict): Health-related information and conditions
          - preferences (Dict): Customer preferences and settings
          - purchase_history (List): Historical purchase data
          - created_at (str): Account creation timestamp
          - updated_at (str): Last update timestamp
          
      Returns None if customer is not found.
  """
  try:
    customer_data = await dynamodb_service.get_customer(customer_id)
    if customer_data:
      print(f'Retrieved customer data for ID: {customer_id}')
      return customer_data
    else:
      print(f'Customer not found: {customer_id}')
      return None
  except Exception as e:
    print(f'Error fetching customer data for {customer_id}: {str(e)}')
    return None
