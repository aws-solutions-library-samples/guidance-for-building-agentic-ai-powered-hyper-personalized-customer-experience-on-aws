from strands import Agent, tool
from strands_tools import image_reader
from agents.tools import search_products, get_customer_data
from strands.models import BedrockModel
from config.settings import get_settings
from utils.streaming_utils import search_callbacks
import asyncio

settings = get_settings()

SEARCH_AGENT_PROMPT = """You are a specialized Product Search Agent designed to help users find relevant products through two distinct search methods.

## CORE RESPONSIBILITIES

### 1. IMAGE-BASED PRODUCT SEARCH
**When to use:** User provides an image of a product or mentions having an image
**Process:**
- Use the image_reader tool to extract detailed visual information
- Identify product characteristics: brand, type, packaging, form factor
- Combine image analysis with any accompanying text query
- Search for exact matches and similar alternatives
- **Decline if:** Image is blurry, unclear, or doesn't contain identifiable product information

### 2. SPECIFIC PRODUCT SEARCH  
**When to use:** User provides specific product details (brand + product type minimum)
**Requirements for valid search:**
- Must include brand name AND product type (e.g., "Sony Headphones", "Nike Running Shoes")
- Generic terms alone are insufficient (e.g., "headphones", "shoes")
**Process:**
- Search for exact product matches first
- Include similar products from same brand
- Suggest alternatives if exact match unavailable

## DECISION LOGIC
1. **Image present?** → Use Image-Based Search
2. **Specific brand + product mentioned?** → Use Specific Product Search

## OUTPUT GUIDELINES
- **Be concise:** Provide clear, brief responses
- **Structure results:** Present products in order of relevance
- **Include key details:** Product name, brand, key features, intended use

## CONSTRAINTS
- Decline searches for unclear images or insufficient product information
- Do not generate anything, only use the search results directly as it is.
"""

@tool
def search_agent(input_str: str) -> str:
    """
    A specialized Search Agent designed to search for products given an image or specific product name.

    1. Image Search: Extracts details from images and searches for matching products
    2. Specific Product Search: Searches for products when given specific brand/product names
    
    Args:
        input_str (str): Search input that can be:
            - Text query with an image for visual product search
            - Specific product name with brand and type information
    
    Returns:
        str: Search results containing relevant products based on the input type:
            - For image searches: Products matching visual characteristics
            - For specific products: Direct product matches and alternatives
    """
    try:
        # Check if we have any active streaming callback for this agent
        active_callback = search_callbacks.get_active_callback("search_agent")
        
        if active_callback:
            # Run async streaming in sync context
            return asyncio.run(_run_search_agent_async(input_str, active_callback))
        else:
            # Regular synchronous execution
            agent = Agent(
                model=BedrockModel(
                    model_id=settings.BEDROCK_MODEL_ID,
                ),
                system_prompt=SEARCH_AGENT_PROMPT,
                tools=[search_products, image_reader],
                callback_handler=None
            )
            response = agent(input_str)
            return str(response)
    except Exception as e:
        return f"Error in search agent: {str(e)}"

async def _run_search_agent_async(input_str: str, streaming_callback) -> str:
    """Run search agent with streaming support"""
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=SEARCH_AGENT_PROMPT,
            tools=[search_products, image_reader],
            callback_handler=None
        )
        
        accumulated_response = ""
        
        # Stream the agent response
        async for event in agent.stream_async(input_str):
            if isinstance(event, dict) and "data" in event:
                chunk = event["data"]
                accumulated_response += chunk
                await streaming_callback.on_text_chunk(chunk)
            elif isinstance(event, str):
                accumulated_response += event
                await streaming_callback.on_text_chunk(event)
                
        return accumulated_response
        
    except Exception as e:
        error_msg = f"Error in search agent streaming: {str(e)}"
        await streaming_callback.on_text_chunk(error_msg)
        return error_msg

def set_streaming_callback(callback_id: str, websocket_manager=None, websocket=None):
    """Set streaming callback for search agent"""
    search_callbacks.set_callback(callback_id, websocket_manager, websocket)

def clear_streaming_callback(callback_id: str):
    """Clear streaming callback"""
    search_callbacks.clear_callback(callback_id)

async def search_agent_streaming(input_str: str, websocket_manager=None, websocket=None):
    """
    Streaming version of search_agent that yields events for real-time responses.
    
    Args:
        input_str (str): Search query or request
        websocket_manager: WebSocket manager for sending streaming events
        websocket: WebSocket connection for sending streaming events
    
    Yields:
        dict: Streaming events from the search agent
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=SEARCH_AGENT_PROMPT,
            tools=[search_products, get_customer_data],
            callback_handler=None
        )
        
        # Stream the agent response
        async for event in agent.stream_async(input_str):
            # Debug logging to understand event structure
            logger.debug(f"Search agent event type: {type(event)}, content: {event}")
            
            # Handle different event types
            if isinstance(event, dict):
                yield event
            elif isinstance(event, str):
                # If event is a string, wrap it in a data structure
                yield {"data": event}
            else:
                # Convert other types to string and wrap
                yield {"data": str(event)}
            
    except Exception as e:
        logger.error(f"Error in search agent streaming: {str(e)}")
        error_event = {"data": f"Error in search agent: {str(e)}"}
        yield error_event
