from strands import Agent, tool
from strands_tools import file_read, image_reader
from strands.models import BedrockModel
from config.settings import get_settings
from agents.tools import get_customer_data
from utils.streaming_utils import body_comp_callbacks
import asyncio

settings = get_settings()

BODY_COMP_AGENT_PROMPT = """
You are a body composition analyst. Extract and analyze body composition data from any provided source.

EXTRACT:
- Weight, body fat %, muscle mass, BMI, visceral fat
- Fitness goals and progress indicators
- Measurement dates/trends

OUTPUT FORMAT (keep brief):
**Metrics:** [List key values with dates]
**Status:** [2-3 sentence assessment vs. healthy ranges]
**Goals:** [Progress summary if goals mentioned]
**Key Insight:** [Most important observation]
**Recommendation:** [1-2 specific actions]

Be concise and data-focused. If information is missing, state what's available and what would help. Prioritize actionable insights over detailed explanations. Keep responses short.
"""

@tool
def body_composition_analyzer(input_str: str) -> str:
    """
    Analyze body composition data from any source and provide clear insights. Extracts available metrics from text, images, or files and delivers practical analysis.
    
    Args:
        input_str (str): Input containing body composition data. Can be:
            - Text descriptions of body composition metrics
            - File paths to fitness app screenshots or documents
            - User fitness goals and targets
            - Any combination of available data
    
    Returns:
        str: Analysis containing extracted metrics, identified goals, key insights, and practical recommendations based on available data.
    """
    try:
        # Check if we have any active streaming callback for this agent
        active_callback = body_comp_callbacks.get_active_callback("body_composition_analyzer")
                
        if active_callback:
            # Run async streaming in sync context
            return asyncio.run(_run_body_comp_analyzer_async(input_str, active_callback))
        else:
            # Regular synchronous execution
            agent = Agent(
                model=BedrockModel(
                    model_id=settings.BEDROCK_MODEL_ID,
                ),
                system_prompt=BODY_COMP_AGENT_PROMPT,
                tools=[file_read, image_reader, get_customer_data],
                callback_handler=None
            )
            response = agent(input_str)
            return str(response)
    except Exception as e:
        return f"Error in body composition agent: {str(e)}"

async def _run_body_comp_analyzer_async(input_str: str, streaming_callback) -> str:
    """Run body composition analyzer with streaming support"""
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=BODY_COMP_AGENT_PROMPT,
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
        error_msg = f"Error in body composition agent streaming: {str(e)}"
        await streaming_callback.on_text_chunk(error_msg)
        return error_msg

def set_streaming_callback(callback_id: str, websocket_manager=None, websocket=None):
    """Set streaming callback for body composition analyzer"""
    body_comp_callbacks.set_callback(callback_id, websocket_manager, websocket)

def clear_streaming_callback(callback_id: str):
    """Clear streaming callback"""
    body_comp_callbacks.clear_callback(callback_id)

async def body_composition_analyzer_streaming(input_str: str, websocket_manager=None, websocket=None):
    """
    Streaming version of body_composition_analyzer that yields events for real-time responses.
    
    Args:
        input_str (str): Input containing body composition data
        websocket_manager: WebSocket manager for sending streaming events
        websocket: WebSocket connection for sending streaming events
    
    Yields:
        dict: Streaming events from the body composition analyzer
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=BODY_COMP_AGENT_PROMPT,
            tools=[file_read, image_reader, get_customer_data],
            callback_handler=None
        )
        
        # Stream the agent response
        async for event in agent.stream_async(input_str):
            # Debug logging to understand event structure
            logger.debug(f"Body comp agent event type: {type(event)}, content: {event}")
            
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
        logger.error(f"Error in body composition agent streaming: {str(e)}")
        error_event = {"data": f"Error in body composition agent: {str(e)}"}
        yield error_event
