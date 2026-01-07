from strands import Agent, tool
from strands_tools import file_read, image_reader
from strands.models import BedrockModel
from config.settings import get_settings
from agents.tools import get_customer_data
from utils.streaming_utils import bloodwork_callbacks
import asyncio

settings = get_settings()

BLOODWORK_AGENT_PROMPT = """
You are a bloodwork analyzer. Extract and analyze laboratory test results from any provided source.

EXTRACT:
- Lab values, units, reference ranges, test dates
- CBC, CMP, lipid panel, thyroid, other markers
- Values outside normal ranges

OUTPUT FORMAT (keep brief):
**Test Date:** [Date if available]
**Key Values:** [Abnormal results with ranges]
**Normal Range:** [Values within expected limits]
**Concerning:** [Critical/significantly abnormal findings]
**Trends:** [Changes over time if multiple dates]
**Completeness:** [complete|partial|unclear]

Be concise and data-focused. Flag only significantly abnormal values. If unclear input, state "unclear" completeness. No medical advice - analytical observations only. Keep responses short.
"""

@tool
def bloodwork_analyzer(input_str: str) -> str:
    """
    Analyze laboratory blood test results from PDF documents or images. A specialized agent that extracts and interprets bloodwork/lab values, identifies values outside normal reference ranges, flags concerning values, and provides structured medical analysis in JSON format.
    
    Args:
        input_str (str): Input containing bloodwork data. Can be:
            - File path to a PDF document with lab results
            - File path to an image of lab results
            - Direct text description of bloodwork values
            - Any combination of the above but must contain bloodwork data
    
    Returns:
        str: string containing:
            - analysis_summary: Brief overall assessment
            - extracted_values: List of test results with values, ranges, and status
            - concerning_findings: List of abnormal values requiring attention
            - recommendations: Actionable recommendations based on findings
            - test_date: Date of tests if available
            - completeness: Indicator of data quality (complete|partial|unclear)
    """
    try:
        # Check if we have any active streaming callback for this agent
        active_callback = bloodwork_callbacks.get_active_callback("bloodwork_analyzer")
                
        if active_callback:
            # Run async streaming in sync context
            return asyncio.run(_run_bloodwork_analyzer_async(input_str, active_callback))
        else:
            # Regular synchronous execution
            agent = Agent(
                model=BedrockModel(
                    model_id=settings.BEDROCK_MODEL_ID,
                ),
                system_prompt=BLOODWORK_AGENT_PROMPT,
                tools=[file_read, image_reader, get_customer_data],
                callback_handler=None
            )
            response = agent(input_str)
            return str(response)
    except Exception as e:
        return f"Error in bloodwork agent: {str(e)}"

async def _run_bloodwork_analyzer_async(input_str: str, streaming_callback) -> str:
    """Run bloodwork analyzer with streaming support"""
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=BLOODWORK_AGENT_PROMPT,
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
        error_msg = f"Error in bloodwork agent streaming: {str(e)}"
        await streaming_callback.on_text_chunk(error_msg)
        return error_msg

def set_streaming_callback(callback_id: str, websocket_manager=None, websocket=None):
    """Set streaming callback for bloodwork analyzer"""
    bloodwork_callbacks.set_callback(callback_id, websocket_manager, websocket)

def clear_streaming_callback(callback_id: str):
    """Clear streaming callback"""
    bloodwork_callbacks.clear_callback(callback_id)

async def bloodwork_analyzer_streaming(input_str: str, websocket_manager=None, websocket=None):
    """
    Streaming version of bloodwork_analyzer that yields events for real-time responses.
    
    Args:
        input_str (str): Input containing bloodwork data
        websocket_manager: WebSocket manager for sending streaming events
        websocket: WebSocket connection for sending streaming events
    
    Yields:
        dict: Streaming events from the bloodwork analyzer
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        agent = Agent(
            model=BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID,
            ),
            system_prompt=BLOODWORK_AGENT_PROMPT,
            tools=[file_read, image_reader, get_customer_data],
            callback_handler=None
        )
        
        # Stream the agent response
        async for event in agent.stream_async(input_str):
            # Debug logging to understand event structure
            logger.debug(f"Bloodwork agent event type: {type(event)}, content: {event}")
            
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
        logger.error(f"Error in bloodwork agent streaming: {str(e)}")
        error_event = {"data": f"Error in bloodwork agent: {str(e)}"}
        yield error_event
