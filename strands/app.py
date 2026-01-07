from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import logging
import uuid
import re
from contextlib import asynccontextmanager
from strands import Agent
from strands.models import BedrockModel

from config.settings import get_settings
from models.schemas import (
    CustomerCreate, CustomerResponse,
    SearchRequest, SearchResponse, SemanticSearchRequest,
    APIResponse, HealthCheck,
    WebSocketMessage, WebSocketResponse, Recommendations, Product
)
from services.dynamodb_service import dynamodb_service
from services.opensearch_service import opensearch_service
from utils.catalog_loader import catalog_loader
from utils.websocket_utils import ConnectionManager
from agents.hyperpersonal_search import create_hyperpersonal_search_agent

settings = get_settings()

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(name)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    logger.info("Starting CX VHS Product Catalog API")
    try:
        services = {}
        try:
            dynamodb_health = await dynamodb_service.health_check()
            services['dynamodb'] = dynamodb_health['status']
        except Exception as e:
            services['dynamodb'] = f'unhealthy: {str(e)}'

        try:
            opensearch_health = await opensearch_service.health_check()
            services['opensearch'] = opensearch_health['status']
        except Exception as e:
            services['opensearch'] = f'unhealthy: {str(e)}'

        try:
            # Test agent creation but don't store globally
            test_agent = create_hyperpersonal_search_agent()
            services['agentic'] = "healthy"
        except Exception as e:
            services['agentic'] = f"unhealthy: {str(e)}"

        
        overall_status = "healthy" if all(
            status == "healthy" for status in services.values() 
            if not status.startswith("unhealthy")
        ) else "degraded"

        logger.info(f"Startup health check: {overall_status}")
    except Exception as e:
        logger.warning(f"Startup health check failed: {str(e)}")
    
    yield

    logger.info("Shutting down CX VHS Product Catalog API")

app = FastAPI(
    title='CX VHS - Product Catalog API',
    description='AI-powered product search and customer management platform',
    version='1.0.0',
    debug=settings.DEBUG,
    lifespan=lifespan,
    root_path="/api",  # Handle /api prefix from ALB
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()

async def extract_recommendations_from_text(text: str, user_id: str) -> Recommendations:
    """
    Extract product recommendations from text using text-based parsing to avoid circular references.
    Returns a Recommendations object with extracted products or empty list if none found.
    """
    try:
        extraction_agent = Agent(
            model=BedrockModel(model_id=settings.BEDROCK_MODEL_ID),
            system_prompt="You extract product recommendations from text and return valid JSON.",
            tools=[],
            callback_handler=None,
        )
        
        # Improved prompt for JSON extraction
        extraction_prompt = f"""
        Based on the recent conversation and response: "{text}"
        
        Extract any specific product recommendations that were mentioned.
        Return ONLY a valid JSON object in this exact format:
        {{
            "recommendations": [
                {{
                    "product_id": "PROD001",
                    "product_name": "Product Name",
                    "reason": "Why it was recommended",
                    "confidence_score": 85
                }}
            ]
        }}
        
        If no specific products were recommended, return: {{"recommendations": []}}
        Return ONLY the JSON, no other text.
        """
        
        # Use regular async call instead of structured_output_async
        extraction_response = await extraction_agent.invoke_async(extraction_prompt)
        
        # Parse the JSON response
        try:
            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r'\{.*\}', str(extraction_response), re.DOTALL)
            if json_match:
                json_str = json_match.group()
                recs_data = json.loads(json_str)
                # Create Recommendations object manually
                recommendations = Recommendations(
                    recommendations=[
                        Product(**rec) for rec in recs_data.get('recommendations', [])
                    ]
                )
            else:
                recommendations = Recommendations(recommendations=[])
        except (json.JSONDecodeError, Exception) as parse_error:
            logger.warning(f"Failed to parse extraction response for user {user_id}: {parse_error}")
            recommendations = Recommendations(recommendations=[])
        
        logger.info(f"Extracted {len(recommendations.recommendations)} recommendations for user {user_id}")
        return recommendations
        
    except Exception as e:
        logger.error(f"Text-based extraction failed for user {user_id}: {e}")
        return Recommendations(recommendations=[])

@app.get('/health', response_model=HealthCheck)
async def health_check():
    """Health check for all services"""
    try:
        services = {}
        try:
            dynamodb_health = await dynamodb_service.health_check()
            services['dynamodb'] = dynamodb_health['status']
        except Exception as e:
            services['dynamodb'] = f'unhealthy: {str(e)}'

        try:
            opensearch_health = await opensearch_service.health_check()
            services['opensearch'] = opensearch_health['status']
        except Exception as e:
            services['opensearch'] = f'unhealthy: {str(e)}'

        try:
            # Test agent creation but don't store globally
            test_agent = create_hyperpersonal_search_agent()
            services['agentic'] = "healthy"
        except Exception as e:
            services['agentic'] = f"unhealthy: {str(e)}"

        overall_status = "healthy" if all(
            status == "healthy" for status in services.values() 
            if not status.startswith("unhealthy")
        ) else "degraded"

        return HealthCheck(status=overall_status, services=services)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")


def _ensure_relative_image_urls(products):
    """Ensure all product image URLs are relative paths for CloudFront"""
    import re
    
    for product in products:
        if 'image_url' in product and product['image_url']:
            image_url = product['image_url']
            
            # If it's a full S3 URL, convert it back to relative path
            if 's3.amazonaws.com' in image_url or 's3-' in image_url:
                # Extract the path after /images/
                match = re.search(r'/images/([^?]+)', image_url)
                if match:
                    product['image_url'] = f"/images/{match.group(1)}"
                    logger.info(f"Converted S3 URL to relative path: {image_url} -> {product['image_url']}")
                else:
                    # Fallback: ensure it starts with /images/
                    if not image_url.startswith('/images/'):
                        filename = image_url.split('/')[-1] if '/' in image_url else image_url
                        product['image_url'] = f"/images/{filename}"
            # Ensure relative paths start with /images/
            elif not image_url.startswith('/images/') and not image_url.startswith('http'):
                product['image_url'] = f"/images/{image_url}"
    
    return products

@app.post('/search/keyword', response_model=SearchResponse)
async def keyword_search(request: SearchRequest):
    """Perform keyword-based product search"""
    try:
        results = await catalog_loader.search_products_by_query(
            query=request.query,
            search_type="keyword",
            filters=request.filters,
            size=request.size
        )

        # Ensure all image URLs are relative paths for CloudFront
        processed_results = _ensure_relative_image_urls(results.get('results', []))

        search_history = {
            "search_id": str(uuid.uuid4()),
            "user_id": None,
            "query": request.query,
            "search_type": "keyword",
            "results_count": results.get('total_hits', 0),
            "filters_applied": request.filters or {}
        }

        try:
            await dynamodb_service.save_search_history(search_history)
        except Exception as e:
            logger.warning(f"Failed to save search history: {str(e)}")

        return SearchResponse(
            query=request.query,
            total_hits=results.get('total_hits', 0),
            results=processed_results,
            **{"from": request.from_},
            size=request.size,
            took_ms=results.get('took_ms')
        )

    except Exception as e:
        logger.error(f"Keyword search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Keyword search failed: {str(e)}")

@app.post('/search/semantic', response_model=SearchResponse)
async def semantic_search(request: SemanticSearchRequest):
    """Perform AI-powered semantic search"""
    try:
        results = await catalog_loader.search_products_by_query(
            query=request.query,
            search_type="semantic",
            filters=request.filters,
            size=request.size
        )

        # Ensure all image URLs are relative paths for CloudFront
        processed_results = _ensure_relative_image_urls(results.get('results', []))

        return SearchResponse(
            query=request.query,
            total_hits=results.get('total_hits', 0),
            results=processed_results,
            **{"from": request.from_},
            size=request.size,
            took_ms=results.get('took_ms')
        )
        
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")

@app.post('/customers', response_model=CustomerResponse)
async def create_customer(customer: CustomerCreate):
    """Create a new customer with full data structure"""
    try:
        customer_data = customer.model_dump()
        result = await dynamodb_service.create_customer(customer_data)
        return CustomerResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create customer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create customer: {str(e)}")

@app.get('/customers', response_model=APIResponse)
async def list_customers():
    """Get list of available customers for login simulation"""
    try:
        # Fetch customers from DynamoDB
        customer_list = await dynamodb_service.list_customers()
        
        return APIResponse(
            message="Customers retrieved successfully",
            data={
                "customers": customer_list,
                "total_count": len(customer_list)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get customers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get customers: {str(e)}")

@app.get('/customers/{customer_id}', response_model=APIResponse)
async def get_customer(customer_id: str):
    """Get customer by ID from DynamoDB for login simulation"""
    try:
        # Fetch customer from DynamoDB
        customer = await dynamodb_service.get_customer(customer_id)
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
            
        return APIResponse(
            message="Customer retrieved successfully",
            data={"customer": customer}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get customer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get customer: {str(e)}")

@app.websocket("/ws/chat/{user_id}")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat with file upload support"""
    await manager.connect(websocket, user_id)

    # Send welcome message
    welcome_response = WebSocketResponse(
        type="system",
        message=f"Welcome! User {user_id} connected to the Hyperpersonal Assistant 🤖",
        user_id="system"
    )
    success = await manager.send_personal_message(welcome_response.model_dump_json(), websocket)
    if not success:
        logger.warning(f"Failed to send welcome message to user {user_id}")
        return
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse incoming message
                message_data = json.loads(data)
                ws_message = WebSocketMessage(**message_data)
                
                # Handle different message types
                if ws_message.type == "chat":
                    await handle_chat_message(websocket, user_id, ws_message)
                elif ws_message.type == "file_upload":
                    await handle_file_upload(websocket, user_id, ws_message)
                else:
                    error_response = WebSocketResponse(
                        type="error",
                        message=f"Unknown message type: {ws_message.type}",
                        user_id="system"
                    )
                    await manager.send_personal_message(error_response.model_dump_json(), websocket)
                    
            except json.JSONDecodeError:
                error_response = WebSocketResponse(
                    type="error",
                    message="Invalid JSON format",
                    user_id="system"
                )
                await manager.send_personal_message(error_response.model_dump_json(), websocket)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                error_response = WebSocketResponse(
                    type="error",
                    message=f"Error processing message: {str(e)}",
                    user_id="system"
                )
                await manager.send_personal_message(error_response.model_dump_json(), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info(f"User {user_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)

async def handle_chat_message(websocket: WebSocket, user_id: str, ws_message: WebSocketMessage):
    """Handle chat messages and integrate with hyperpersonal search assistant using streaming"""
    try:
        
        user_message = ws_message.message
        if not user_message:
            error_response = WebSocketResponse(
                type="error",
                message="Empty message received",
                user_id="system"
            )
            await manager.send_personal_message(error_response.model_dump_json(), websocket)
            return

        # Send typing indicator
        typing_response = WebSocketResponse(
            type="system",
            message="Assistant is thinking...",
            user_id="system"
        )
        await manager.send_personal_message(typing_response.model_dump_json(), websocket)

        # Get or create user-specific agent
        user_agent = manager.get_user_agent(user_id)
        if user_agent is None:
            # Create a fresh agent for this user
            user_agent = create_hyperpersonal_search_agent()
            manager.set_user_agent(user_id, user_agent)
            logger.info(f"Created fresh agent for user {user_id}")

        # Get user's uploaded files for context
        user_files = manager.get_user_files(user_id)
        
        # Get customer_id if provided for personalization
        customer_id = ws_message.customer_id
        
        # Enhance user message with file context and customer_id if available
        enhanced_message = user_message
        if user_files:
            file_context = f"\n\nUploaded files available for analysis: {', '.join(user_files)}"
            enhanced_message += file_context
            
        # Add customer_id to message if provided for agent personalization
        if customer_id:
            customer_context = f"\n\nCustomer ID: {customer_id}"
            enhanced_message += customer_context
            logger.info(f"Added customer_id context for personalization: {customer_id}")

        # Stream response from user-specific hyperpersonal search assistant
        accumulated_response = ""
        
        try:
            # Use stream_async to get streaming events
            async for event in user_agent.stream_async(enhanced_message):
                # Debug: Log all events to understand structure
                logger.debug(f"Received streaming event: {event}")
                
                # Handle different event types
                if "data" in event:
                    # Stream text chunks to the client
                    chunk = event["data"]
                    accumulated_response += chunk
                    
                    # Send streaming chunk
                    stream_response = WebSocketResponse(
                        type="stream",
                        message=chunk,
                        user_id="assistant"
                    )
                    await manager.send_personal_message(stream_response.model_dump_json(), websocket)
                
                # Handle completion event - try multiple possible completion indicators
                elif event.get("complete", False) or event.get("type") == "complete" or event.get("event") == "complete":
                    # Send completion for this message cycle
                    try:
                        # Use helper function for text-based extraction
                        logger.info(f"Attempting text-based extraction for user {user_id}")
                        recs = await extract_recommendations_from_text(accumulated_response, user_id)
                        
                        if recs and recs.recommendations:  # Only send if there are actual recommendations
                            logger.info(f"Sending structured recommendations to user {user_id}: {[r.product_name for r in recs.recommendations]}")
                            recs_response = WebSocketResponse(
                                type="structured_recommendations",
                                message=recs.model_dump_json(),
                                user_id="assistant"
                            )
                            await manager.send_personal_message(recs_response.model_dump_json(), websocket)
                        else:
                            # Send regular chat completion if no recommendations
                            complete_response = WebSocketResponse(
                                type="chat_complete",
                                message=accumulated_response,
                                user_id="assistant"
                            )
                            await manager.send_personal_message(complete_response.model_dump_json(), websocket)
                    except Exception as e:
                        logger.error(f"Structured output failed for user {user_id}: {e}")
                        # Fallback to regular completion
                        complete_response = WebSocketResponse(
                            type="chat_complete",
                            message=accumulated_response,
                            user_id="assistant"
                        )
                        await manager.send_personal_message(complete_response.model_dump_json(), websocket)
                    
                    # Reset accumulation for next message
                    accumulated_response = ""
                    # Note: Don't break here, continue to handle multiple cycles
                    
                # Handle tool usage events for transparency and subagent streaming
                elif "current_tool_use" in event and event["current_tool_use"].get("name"):
                    tool_name = event["current_tool_use"]["name"]
                    
                    # Send message boundary for current message before tool/subagent takes control
                    if accumulated_response.strip():  # Only send if there's content
                        boundary_response = WebSocketResponse(
                            type="message_boundary",
                            message=accumulated_response,
                            user_id="assistant"
                        )
                        await manager.send_personal_message(boundary_response.model_dump_json(), websocket)
                        
                        # Reset accumulation for next message
                        accumulated_response = ""
                    
                    # Send tool usage notification
                    tool_response = WebSocketResponse(
                        type="system",
                        message=f"Using {tool_name}...",
                        user_id="system"
                    )
                    await manager.send_personal_message(tool_response.model_dump_json(), websocket)
                    
                    # Set up global streaming context for supported sub-agents
                    callback_id = f"{user_id}_{tool_name}_{uuid.uuid4().hex[:8]}"
                    
                    if tool_name in ["search_agent", "bloodwork_analyzer", "body_composition_analyzer"]:
                        try:
                            # Set global streaming context that sub-agents can detect
                            if tool_name == "search_agent":
                                from agents.search_agent import set_streaming_callback
                                set_streaming_callback(callback_id, manager, websocket)
                            elif tool_name == "bloodwork_analyzer":
                                from agents.bloodwork_agent import set_streaming_callback
                                set_streaming_callback(callback_id, manager, websocket)
                            elif tool_name == "body_composition_analyzer":
                                from agents.body_comp_agent import set_streaming_callback
                                set_streaming_callback(callback_id, manager, websocket)
                                
                            logger.debug(f"Set up streaming callback for {tool_name} with ID: {callback_id}")
                            
                        except Exception as callback_error:
                            logger.error(f"Error setting up {tool_name} streaming callback: {callback_error}")
                
                # Handle tool completion events to cleanup streaming callbacks
                elif "tool_result" in event and "current_tool_use" in event:
                    tool_name = event["current_tool_use"].get("name")
                    # Clean up streaming callbacks
                    if tool_name in ["search_agent", "bloodwork_analyzer", "body_composition_analyzer"]:
                        try:
                            if tool_name == "search_agent":
                                from agents.search_agent import clear_streaming_callback
                                # Clear all callbacks for this user (simple approach)
                                clear_streaming_callback(f"{user_id}_{tool_name}")
                            elif tool_name == "bloodwork_analyzer":
                                from agents.bloodwork_agent import clear_streaming_callback
                                clear_streaming_callback(f"{user_id}_{tool_name}")
                            elif tool_name == "body_composition_analyzer":
                                from agents.body_comp_agent import clear_streaming_callback
                                clear_streaming_callback(f"{user_id}_{tool_name}")
                                
                        except Exception as cleanup_error:
                            logger.debug(f"Error cleaning up {tool_name} streaming callback: {cleanup_error}")
                    
            # Fallback completion handler - if no explicit completion event was received
            # but we have accumulated response, try to extract recommendations
            if accumulated_response.strip():
                logger.info(f"Streaming ended without explicit completion event for user {user_id}, attempting fallback extraction")
                try:
                    # Use helper function for fallback text-based extraction
                    recs = await extract_recommendations_from_text(accumulated_response, user_id)
                    
                    if recs and recs.recommendations:  # Only send if there are actual recommendations
                        logger.info(f"Sending fallback structured recommendations to user {user_id}: {[r.product_name for r in recs.recommendations]}")
                        recs_response = WebSocketResponse(
                            type="structured_recommendations",
                            message=recs.model_dump_json(),
                            user_id="assistant"
                        )
                        await manager.send_personal_message(recs_response.model_dump_json(), websocket)
                    else:
                        # Send regular chat completion if no recommendations
                        complete_response = WebSocketResponse(
                            type="chat_complete",
                            message=accumulated_response,
                            user_id="assistant"
                        )
                        await manager.send_personal_message(complete_response.model_dump_json(), websocket)
                except Exception as e:
                    logger.error(f"Fallback structured output failed for user {user_id}: {e}")
                    # Final fallback to regular completion
                    complete_response = WebSocketResponse(
                        type="chat_complete",
                        message=accumulated_response,
                        user_id="assistant"
                    )
                    await manager.send_personal_message(complete_response.model_dump_json(), websocket)
                    
        except Exception as stream_error:
            logger.error(f"Error in streaming: {stream_error}")
            # Fallback to non-streaming response
            assistant_response = str(user_agent(enhanced_message))
            chat_response = WebSocketResponse(
                type="chat",
                message=assistant_response,
                user_id="assistant"
            )
            await manager.send_personal_message(chat_response.model_dump_json(), websocket)
        
    except Exception as e:
        logger.error(f"Error in chat handler: {e}")
        error_response = WebSocketResponse(
            type="error",
            message=f"Error processing chat message: {str(e)}",
            user_id="system"
        )
        await manager.send_personal_message(error_response.model_dump_json(), websocket)

async def handle_file_upload(websocket: WebSocket, user_id: str, ws_message: WebSocketMessage):
    """Handle file uploads from WebSocket messages"""
    try:
        if not ws_message.files:
            error_response = WebSocketResponse(
                type="error",
                message="No files provided in file_upload message",
                user_id="system"
            )
            await manager.send_personal_message(error_response.model_dump_json(), websocket)
            return

        uploaded_files = []
        
        for file_upload in ws_message.files:
            # Validate file type
            allowed_types = [
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
                'application/pdf', 'text/plain', 'application/json'
            ]
            
            if file_upload.file_type not in allowed_types:
                error_response = WebSocketResponse(
                    type="error",
                    message=f"File type {file_upload.file_type} not allowed. Supported types: images (JPEG, PNG, GIF, WebP) and PDF",
                    user_id="system"
                )
                await manager.send_personal_message(error_response.model_dump_json(), websocket)
                continue

            # Save file
            file_path = await manager.save_uploaded_file(
                user_id=user_id,
                file_data=file_upload.file_data,
                filename=file_upload.filename,
                file_type=file_upload.file_type
            )
            
            if file_path:
                uploaded_files.append({
                    'filename': file_upload.filename,
                    'file_type': file_upload.file_type,
                    'file_path': file_path,
                    'size': file_upload.size
                })
            else:
                error_response = WebSocketResponse(
                    type="error",
                    message=f"Failed to save file: {file_upload.filename}",
                    user_id="system"
                )
                await manager.send_personal_message(error_response.model_dump_json(), websocket)

        # Send confirmation of uploaded files
        if uploaded_files:
            success_response = WebSocketResponse(
                type="file_saved",
                message=f"Successfully uploaded {len(uploaded_files)} file(s)",
                data={"uploaded_files": uploaded_files},
                user_id="system"
            )
            await manager.send_personal_message(success_response.model_dump_json(), websocket)
            
            # If there's also a message, process it as a chat message
            if ws_message.message:
                await handle_chat_message(websocket, user_id, ws_message)
        
    except Exception as e:
        logger.error(f"Error in file upload handler: {e}")
        error_response = WebSocketResponse(
            type="error",
            message=f"Error processing file upload: {str(e)}",
            user_id="system"
        )
        await manager.send_personal_message(error_response.model_dump_json(), websocket)

if __name__ == '__main__':
    uvicorn.run(
        app, 
        host='127.0.0.1', 
        port=settings.PORT,
        log_level="info" if not settings.DEBUG else "debug"
    )
