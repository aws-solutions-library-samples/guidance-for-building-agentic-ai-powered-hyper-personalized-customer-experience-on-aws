import uuid
from strands import tool
from utils.catalog_loader import catalog_loader
from services.dynamodb_service import dynamodb_service

@tool
async def search_products(query: str, search_type: str = "keyword"):
  """
  Search for products using keyword or semantic search.
  
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

@tool
async def place_order(customer_id: str, product_items: list, shipping_address: dict = None, payment_method: str = "default"):
  """
  Place a new order for a customer and save it to the DynamoDB orders table.
  
  Args:
      customer_id (str): The unique identifier for the customer placing the order
      product_items (list): List of product items to order. Each item should be a dict with:
          - product_id (str): Unique product identifier
          - product_name (str): Name of the product
          - quantity (int): Number of items to order
          - unit_price (float): Price per unit
          - subtotal (float): Total price for this item (quantity * unit_price)
      shipping_address (dict, optional): Shipping address override. If not provided, uses customer's default address.
          Should contain: street, city, state, zip_code, country
      payment_method (str, optional): Payment method to use. Defaults to "default"
      
  Returns:
      Dict[str, Any]: Order confirmation containing:
          - order_id (str): Unique order identifier
          - customer_id (str): Customer who placed the order
          - product_items (List): List of ordered items
          - total_amount (float): Total order amount
          - order_date (str): ISO timestamp when order was placed
          - status (str): Order status (initially 'pending')
          - shipping_address (Dict): Delivery address
          - payment_method (str): Payment method used
          - estimated_delivery (str): Estimated delivery date
          
      Returns None if order creation fails.
  """
  try:
    # Generate unique order ID
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    # Calculate total amount
    total_amount = sum(float(item.get('subtotal', 0)) for item in product_items)
    
    # Get customer data for default shipping address if needed
    customer_data = await dynamodb_service.get_customer(customer_id)
    if not customer_data:
      print(f'Customer not found: {customer_id}')
      return None
    
    # Use provided shipping address or default to customer's address
    if shipping_address is None:
      customer_address = customer_data.get('personal_info', {}).get('address', {})
      shipping_address = {
        'street': customer_address.get('street', ''),
        'city': customer_address.get('city', ''),
        'state': customer_address.get('state', ''),
        'zip_code': customer_address.get('zip_code', ''),
        'country': customer_address.get('country', 'US')
      }
    
    # Calculate estimated delivery (7 business days from now)
    from datetime import datetime, timedelta
    estimated_delivery = (datetime.now() + timedelta(days=7)).isoformat()
    
    # Create order data
    order_data = {
      'order_id': order_id,
      'customer_id': customer_id,
      'product_items': product_items,
      'total_amount': total_amount,
      'shipping_address': shipping_address,
      'payment_method': payment_method,
      'estimated_delivery': estimated_delivery,
      'status': 'pending'
    }
    
    # Save order to DynamoDB
    created_order = await dynamodb_service.create_order(order_data)
    
    if created_order:
      print(f'Order placed successfully: {order_id} for customer {customer_id}')
      return created_order
    else:
      print(f'Failed to create order for customer {customer_id}')
      return None
      
  except Exception as e:
    print(f'Error placing order for customer {customer_id}: {str(e)}')
    return None

@tool
async def get_customer_orders(customer_id: str, limit: int = 10):
  """
  Retrieve order history for a specific customer.
  
  Args:
      customer_id (str): The unique identifier for the customer
      limit (int, optional): Maximum number of orders to return. Defaults to 10.
      
  Returns:
      List[Dict[str, Any]]: List of customer orders, sorted by most recent first. Each order contains:
          - order_id (str): Unique order identifier
          - customer_id (str): Customer who placed the order
          - product_items (List): List of ordered items
          - total_amount (float): Total order amount
          - order_date (str): ISO timestamp when order was placed
          - status (str): Current order status
          - shipping_address (Dict): Delivery address
          - estimated_delivery (str): Estimated delivery date
          
      Returns empty list if no orders found or error occurs.
  """
  try:
    orders = await dynamodb_service.get_customer_orders(customer_id, limit)
    if orders:
      print(f'Retrieved {len(orders)} orders for customer {customer_id}')
      return orders
    else:
      print(f'No orders found for customer {customer_id}')
      return []
      
  except Exception as e:
    print(f'Error retrieving orders for customer {customer_id}: {str(e)}')
    return []
