from strands import Agent, tool
from strands_tools import file_read, image_reader
from strands.models import BedrockModel
from config.settings import get_settings
from agents.tools import get_customer_data
from utils.streaming_utils import bloodwork_callbacks
import asyncio

settings = get_settings()

SALES_AGENT_PROMPT = """
You are an automotive sales assistant. Help customers with vehicle recommendations, automotive product selection, and sales inquiries based on their needs and preferences.

ANALYZE:
- Customer requirements (budget, usage, preferences)
- Vehicle specifications and features
- Market comparisons and options
- Financing and purchase considerations

OUTPUT FORMAT (keep focused):
**Budget Analysis:** [Budget range and financing options]
**Vehicle Recommendations:** [Specific models matching criteria]
**Key Features:** [Important features for customer needs]
**Comparisons:** [How options compare on key factors]
**Next Steps:** [Recommended actions for purchase process]
**Availability:** [Current inventory or delivery timelines]

Be helpful and sales-focused. Provide clear recommendations based on customer needs. Focus on matching vehicles to specific use cases and budgets. Keep responses practical and actionable.
"""

@tool
def sales_assistant(input_str: str) -> str:
    """
    Assist with vehicle recommendations, automotive product selection, and sales inquiries based on customer needs and preferences. A specialized agent that analyzes customer requirements, compares vehicle options, provides market insights, and offers personalized automotive purchase guidance.
    
    Args:
        input_str (str): Input containing sales inquiry data. Can be:
            - Customer requirements and preferences
            - Budget and financing information
            - Vehicle comparison requests
            - Specific model inquiries
            - Any combination related to automotive sales
    
    Returns:
        str: string containing:
            - recommendation_summary: Brief overview of recommendations
            - vehicle_options: List of recommended vehicles with key specs
            - budget_analysis: Financing options and cost breakdown
            - feature_comparison: Key features comparison across options
            - next_steps: Recommended actions for customer
            - availability_info: Current inventory and delivery information
    """
    try:
        # Check if we have any active streaming callback for this agent
        active_callback = bloodwork_callbacks.get_active_callback("sales_assistant")
                
        if active_callback:
            # Run async streaming in sync context
            return asyncio.run(_run_sales_assistant_async(input_str, active_callback))
        else:
            # Regular synchronous execution
            agent = Agent(
                model=BedrockModel(
                    model_id=settings.BEDROCK_MODEL_ID,
                ),
                system_prompt=SALES_AGENT_PROMPT,
                tools=[file_read, image_reader, get_customer_data],
                callback_handler=None
            )
            response = agent(input_str)
            return str(response)
    except Exception as e:
        return f"Error in sales agent: {str(e)}"

async def _run_sales_assistant_async(input_str: str, streaming_callback) -> str:
    """Run sales assistant with streaming support"""
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=SALES_AGENT_PROMPT,
            tools=[file_read, image_reader, get_customer_data],
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
        error_msg = f"Error in sales agent streaming: {str(e)}"
        await streaming_callback.on_text_chunk(error_msg)
        return error_msg

def set_streaming_callback(callback_id: str, websocket_manager=None, websocket=None):
    """Set streaming callback for sales assistant"""
    bloodwork_callbacks.set_callback(callback_id, websocket_manager, websocket)

def clear_streaming_callback(callback_id: str):
    """Clear streaming callback"""
    bloodwork_callbacks.clear_callback(callback_id)

async def sales_assistant_streaming(input_str: str, websocket_manager=None, websocket=None):
    """
    Streaming version of sales_assistant that yields events for real-time responses.
    
    Args:
        input_str (str): Input containing sales inquiry data
        websocket_manager: WebSocket manager for sending streaming events
        websocket: WebSocket connection for sending streaming events
    
    Yields:
        dict: Streaming events from the sales assistant
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=SALES_AGENT_PROMPT,
            tools=[file_read, image_reader, get_customer_data],
            callback_handler=None
        )
        
        # Stream the agent response
        async for event in agent.stream_async(input_str):
            # Debug logging to understand event structure
            logger.debug(f"Sales agent event type: {type(event)}, content: {event}")
            
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
        logger.error(f"Error in sales agent streaming: {str(e)}")
        error_event = {"data": f"Error in sales agent: {str(e)}"}
        yield error_event
