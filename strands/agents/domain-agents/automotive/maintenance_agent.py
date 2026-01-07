from strands import Agent, tool
from strands_tools import file_read, image_reader
from strands.models import BedrockModel
from config.settings import get_settings
from agents.tools import get_customer_data
from utils.streaming_utils import bloodwork_callbacks
import asyncio

settings = get_settings()

MAINTENANCE_AGENT_PROMPT = """
You are an automotive maintenance specialist. Provide vehicle maintenance advice, service recommendations, and automotive care guidance based on vehicle history and usage patterns.

ANALYZE:
- Vehicle maintenance history and current condition
- Mileage, age, and usage patterns
- Manufacturer maintenance schedules
- Preventive maintenance opportunities
- Cost-effective service priorities

OUTPUT FORMAT (keep practical):
**Current Status:** [Overall vehicle condition assessment]
**Immediate Needs:** [Urgent maintenance items requiring attention]
**Upcoming Services:** [Scheduled maintenance in next 6 months]
**Preventive Care:** [Recommended preventive measures]
**Cost Estimates:** [Approximate service costs and priorities]
**Timeline:** [Recommended service scheduling]

Be practical and maintenance-focused. Prioritize safety-critical items. Provide cost-effective maintenance strategies. Focus on extending vehicle life and preventing major repairs. Keep responses actionable and specific.
"""

@tool
def maintenance_specialist(input_str: str) -> str:
    """
    Provide vehicle maintenance advice, service recommendations, and automotive care guidance based on vehicle history and usage. A specialized agent that analyzes maintenance needs, schedules services, estimates costs, and provides preventive care recommendations.
    
    Args:
        input_str (str): Input containing maintenance inquiry data. Can be:
            - Vehicle information (make, model, year, mileage)
            - Maintenance history and records
            - Current vehicle issues or symptoms
            - Service scheduling requests
            - Any combination related to automotive maintenance
    
    Returns:
        str: string containing:
            - maintenance_summary: Brief overview of current maintenance status
            - immediate_needs: Urgent maintenance items requiring attention
            - scheduled_services: Upcoming maintenance based on manufacturer schedule
            - preventive_recommendations: Proactive maintenance suggestions
            - cost_analysis: Service cost estimates and priority ranking
            - service_timeline: Recommended scheduling for maintenance items
    """
    try:
        # Check if we have any active streaming callback for this agent
        active_callback = bloodwork_callbacks.get_active_callback("maintenance_specialist")
                
        if active_callback:
            # Run async streaming in sync context
            return asyncio.run(_run_maintenance_specialist_async(input_str, active_callback))
        else:
            # Regular synchronous execution
            agent = Agent(
                model=BedrockModel(
                    model_id=settings.BEDROCK_MODEL_ID,
                ),
                system_prompt=MAINTENANCE_AGENT_PROMPT,
                tools=[file_read, image_reader, get_customer_data],
                callback_handler=None
            )
            response = agent(input_str)
            return str(response)
    except Exception as e:
        return f"Error in maintenance agent: {str(e)}"

async def _run_maintenance_specialist_async(input_str: str, streaming_callback) -> str:
    """Run maintenance specialist with streaming support"""
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=MAINTENANCE_AGENT_PROMPT,
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
        error_msg = f"Error in maintenance agent streaming: {str(e)}"
        await streaming_callback.on_text_chunk(error_msg)
        return error_msg

def set_streaming_callback(callback_id: str, websocket_manager=None, websocket=None):
    """Set streaming callback for maintenance specialist"""
    bloodwork_callbacks.set_callback(callback_id, websocket_manager, websocket)

def clear_streaming_callback(callback_id: str):
    """Clear streaming callback"""
    bloodwork_callbacks.clear_callback(callback_id)

async def maintenance_specialist_streaming(input_str: str, websocket_manager=None, websocket=None):
    """
    Streaming version of maintenance_specialist that yields events for real-time responses.
    
    Args:
        input_str (str): Input containing maintenance inquiry data
        websocket_manager: WebSocket manager for sending streaming events
        websocket: WebSocket connection for sending streaming events
    
    Yields:
        dict: Streaming events from the maintenance specialist
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=MAINTENANCE_AGENT_PROMPT,
            tools=[file_read, image_reader, get_customer_data],
            callback_handler=None
        )
        
        # Stream the agent response
        async for event in agent.stream_async(input_str):
            # Debug logging to understand event structure
            logger.debug(f"Maintenance agent event type: {type(event)}, content: {event}")
            
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
        logger.error(f"Error in maintenance agent streaming: {str(e)}")
        error_event = {"data": f"Error in maintenance agent: {str(e)}"}
        yield error_event
