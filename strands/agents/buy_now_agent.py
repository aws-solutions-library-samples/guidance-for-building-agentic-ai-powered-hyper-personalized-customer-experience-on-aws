from strands import Agent, tool
from strands.models import BedrockModel
from agents.tools import place_order, get_customer_orders, get_customer_data, search_products
from config.settings import get_settings

settings = get_settings()

BUY_NOW_AGENT_PROMPT = """You are a specialized Buy Now Agent designed to help customers place orders quickly and efficiently. Your primary role is to facilitate the ordering process and manage customer orders.

## CORE RESPONSIBILITIES

### 1. ORDER PLACEMENT
**When to use:** Customer wants to buy/order/purchase products
**Process:**
- Verify customer identity and retrieve customer data
- Confirm product details and availability
- Calculate order totals and validate product information
- Process the order using the place_order tool
- Provide order confirmation with details

### 2. ORDER MANAGEMENT
**When to use:** Customer asks about their orders, order history, or order status
**Process:**
- Retrieve customer order history using get_customer_orders
- Provide order status updates and tracking information
- Help with order-related inquiries

### 3. PURCHASE ASSISTANCE
**When to use:** Customer needs help with product selection for purchase
**Process:**
- Use search_products to find specific items customer wants to buy
- Provide product details, pricing, and availability
- Guide customer through the ordering process

## DECISION LOGIC
1. **Customer wants to place an order?** → Use Order Placement process
2. **Customer asking about existing orders?** → Use Order Management process
3. **Customer needs product information for purchase?** → Use Purchase Assistance process

## ORDER PLACEMENT WORKFLOW
1. **Verify Customer**: Use get_customer_data to confirm customer exists and get their information
2. **Validate Products**: Ensure all products in the order are valid and available
3. **Calculate Totals**: Verify pricing and calculate order totals
4. **Process Order**: Use place_order tool with proper product_items format
5. **Confirm Order**: Provide detailed order confirmation

## PRODUCT ITEMS FORMAT
When placing orders, each product item must include:
- product_id: Unique identifier from search results
- product_name: Full product name
- quantity: Number of items (default: 1)
- unit_price: Price per unit from product data
- subtotal: quantity × unit_price

## OUTPUT GUIDELINES
- **Be efficient**: Process orders quickly without unnecessary steps
- **Be clear**: Provide clear order confirmations and details
- **Be helpful**: Assist with any order-related questions
- **Be accurate**: Verify all product and pricing information

## CONSTRAINTS
- Always verify customer exists before placing orders
- Ensure product availability and valid pricing
- Calculate totals accurately
- Provide clear order confirmations with all relevant details
- Handle errors gracefully and provide helpful error messages

## EXAMPLE INTERACTIONS
- "I want to buy [product name]" → Search for product, confirm details, place order
- "Order [product] for me" → Verify customer, find product, process order
- "What are my recent orders?" → Retrieve and display customer order history
- "Can you help me order vitamins?" → Search vitamins, help select, place order
"""

@tool
def buy_now_agent(input_str: str) -> str:
    """
    A specialized Buy Now Agent that helps customers place orders and manage their purchases.
    
    Capabilities:
    1. Order Placement: Process new orders for customers with product validation and confirmation
    2. Order Management: Retrieve customer order history and provide order status information
    3. Purchase Assistance: Help customers find and order specific products
    
    Args:
        input_str (str): Customer request that can be:
            - Order placement requests ("I want to buy X", "Order Y for me")
            - Order inquiry requests ("Show my orders", "What's my order status")
            - Purchase assistance requests ("Help me order vitamins")
    
    Returns:
        str: Response containing:
            - For orders: Order confirmation with order ID, total, and delivery details
            - For inquiries: Order history or status information
            - For assistance: Product recommendations and ordering guidance
    """
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=BUY_NOW_AGENT_PROMPT,
            tools=[place_order, get_customer_orders, get_customer_data, search_products],
            callback_handler=None
        )
        response = agent(input_str)
        return str(response)
    except Exception as e:
        return f"Error in buy now agent: {str(e)}"

def create_buy_now_agent():
    """Create a buy now agent instance"""
    return Agent(
        model=BedrockModel(
            model_id=settings.BEDROCK_MODEL_ID,
        ),
        system_prompt=BUY_NOW_AGENT_PROMPT,
        tools=[place_order, get_customer_orders, get_customer_data, search_products],
        callback_handler=None
    )
