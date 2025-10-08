import { useState, useEffect, useCallback, useRef } from 'react';
import { websocketService, WebSocketService, type ChatMessage, type WebSocketResponse, type FileUpload } from '../services/websocketService';
import type { Product } from '../store/types';
import { filterStreamingContent } from '../utils/messageUtils';

interface Recommendation {
  product_id?: string;
  id?: string;
  product_name?: string;
  name?: string;
  reason?: string;
  description?: string;
  confidence_score?: number;
  similarity?: number;
}

// Function to extract JSON recommendations from text messages
function extractRecommendationsFromText(text: string): Product[] | null {
  try {
    // Look for JSON patterns in the text
    const jsonPatterns = [
      // Look for ```json blocks
      /```(?:json)?\s*(\{[\s\S]*?\})\s*```/gi,
      // Look for raw JSON objects with recommendations
      /\{[\s\S]*?"recommendations"[\s\S]*?\[[\s\S]*?\][\s\S]*?\}/gi,
      // Look for array of recommendations directly
      /\[[\s\S]*?\{[\s\S]*?"product_[id|name]"[\s\S]*?\}[\s\S]*?\]/gi,
      // Look for single JSON objects that might be recommendations
      /\{[\s\S]*?"product_(?:id|name)"[\s\S]*?"reason"[\s\S]*?\}/gi
    ];
    
    for (const pattern of jsonPatterns) {
      const matches = text.match(pattern);
      if (matches) {
        for (const match of matches) {
          try {
            // Clean the match (remove markdown markers and extra whitespace)
            const cleanMatch = match.replace(/```(?:json)?\s*/gi, '').replace(/\s*```/gi, '').trim();
            
            // Try to parse as JSON
            const parsed = JSON.parse(cleanMatch);
            
            // Handle different JSON structures
            let recommendations: Recommendation[] = [];
            
            if (Array.isArray(parsed)) {
              // Direct array of recommendations
              recommendations = parsed;
            } else if (parsed.recommendations && Array.isArray(parsed.recommendations)) {
              // Object with recommendations array
              recommendations = parsed.recommendations;
            } else if (parsed.product_id || parsed.product_name) {
              // Single recommendation object
              recommendations = [parsed];
            }
            
            if (recommendations.length > 0) {
              // Convert to Product format
              return recommendations.map((rec: Recommendation, index: number) => ({
                id: rec.product_id || rec.id || `extracted-${index}`,
                name: rec.product_name || rec.name || 'Unknown Product',
                category: 'Recommended',
                price: 0,
                currency: 'USD',
                description: rec.reason || rec.description || 'No reason provided',
                stock_status: 'In Stock',
                confidence_score: rec.confidence_score || 0,
                similarity: rec.confidence_score ? rec.confidence_score / 10 : 0.5 // Convert to 0-1 scale
              }));
            }
          } catch {
            // Continue to next match if this one fails
            continue;
          }
        }
      }
    }
    
    return null;
  } catch (error) {
    console.debug('Error extracting recommendations from text:', error);
    return null;
  }
}

// Enhanced bracket matching parser for proper nested JSON handling
class BracketMatchingParser {
  private text: string;
  private position: number;
  
  constructor(text: string) {
    this.text = text;
    this.position = 0;
  }
  
  // Find the end of a JSON object starting at given position
  findJsonObjectEnd(startPos: number): number | null {
    this.position = startPos;
    
    // Skip whitespace
    this.skipWhitespace();
    
    if (this.position >= this.text.length || this.text[this.position] !== '{') {
      return null;
    }
    
    return this.parseObject();
  }
  
  // Find the end of a JSON array starting at given position
  findJsonArrayEnd(startPos: number): number | null {
    this.position = startPos;
    
    // Skip whitespace
    this.skipWhitespace();
    
    if (this.position >= this.text.length || this.text[this.position] !== '[') {
      return null;
    }
    
    return this.parseArray();
  }
  
  private parseObject(): number | null {
    if (this.text[this.position] !== '{') return null;
    
    this.position++; // Skip opening brace
    this.skipWhitespace();
    
    // Handle empty object
    if (this.position < this.text.length && this.text[this.position] === '}') {
      return this.position + 1;
    }
    
    // Parse key-value pairs
    while (this.position < this.text.length) {
      // Parse key (must be a string)
      if (!this.parseString()) return null;
      
      this.skipWhitespace();
      
      // Expect colon
      if (this.position >= this.text.length || this.text[this.position] !== ':') return null;
      this.position++; // Skip colon
      this.skipWhitespace();
      
      // Parse value
      if (!this.parseValue()) return null;
      
      this.skipWhitespace();
      
      // Check for comma or closing brace
      if (this.position >= this.text.length) return null;
      
      if (this.text[this.position] === '}') {
        return this.position + 1; // Found complete object
      } else if (this.text[this.position] === ',') {
        this.position++; // Skip comma
        this.skipWhitespace();
        // Continue to next key-value pair
      } else {
        return null; // Invalid character
      }
    }
    
    return null; // Incomplete object
  }
  
  private parseArray(): number | null {
    if (this.text[this.position] !== '[') return null;
    
    this.position++; // Skip opening bracket
    this.skipWhitespace();
    
    // Handle empty array
    if (this.position < this.text.length && this.text[this.position] === ']') {
      return this.position + 1;
    }
    
    // Parse array elements
    while (this.position < this.text.length) {
      // Parse value
      if (!this.parseValue()) return null;
      
      this.skipWhitespace();
      
      // Check for comma or closing bracket
      if (this.position >= this.text.length) return null;
      
      if (this.text[this.position] === ']') {
        return this.position + 1; // Found complete array
      } else if (this.text[this.position] === ',') {
        this.position++; // Skip comma
        this.skipWhitespace();
        // Continue to next element
      } else {
        return null; // Invalid character
      }
    }
    
    return null; // Incomplete array
  }
  
  private parseValue(): boolean {
    this.skipWhitespace();
    
    if (this.position >= this.text.length) return false;
    
    const char = this.text[this.position];
    
    if (char === '"') {
      return this.parseString();
    } else if (char === '{') {
      const end = this.parseObject();
      return end !== null;
    } else if (char === '[') {
      const end = this.parseArray();
      return end !== null;
    } else if (char === 't' && this.text.substr(this.position, 4) === 'true') {
      this.position += 4;
      return true;
    } else if (char === 'f' && this.text.substr(this.position, 5) === 'false') {
      this.position += 5;
      return true;
    } else if (char === 'n' && this.text.substr(this.position, 4) === 'null') {
      this.position += 4;
      return true;
    } else if (char === '-' || (char >= '0' && char <= '9')) {
      return this.parseNumber();
    }
    
    return false;
  }
  
  private parseString(): boolean {
    if (this.text[this.position] !== '"') return false;
    
    this.position++; // Skip opening quote
    
    while (this.position < this.text.length) {
      const char = this.text[this.position];
      
      if (char === '"') {
        this.position++; // Skip closing quote
        return true;
      } else if (char === '\\') {
        // Handle escaped characters
        this.position += 2; // Skip escape sequence
      } else {
        this.position++;
      }
    }
    
    return false; // Incomplete string
  }
  
  private parseNumber(): boolean {
    const start = this.position;
    
    // Handle negative sign
    if (this.text[this.position] === '-') {
      this.position++;
    }
    
    // Must have at least one digit
    if (this.position >= this.text.length || this.text[this.position] < '0' || this.text[this.position] > '9') {
      return false;
    }
    
    // Parse digits
    while (this.position < this.text.length && this.text[this.position] >= '0' && this.text[this.position] <= '9') {
      this.position++;
    }
    
    // Handle decimal point
    if (this.position < this.text.length && this.text[this.position] === '.') {
      this.position++;
      
      // Must have digits after decimal point
      if (this.position >= this.text.length || this.text[this.position] < '0' || this.text[this.position] > '9') {
        return false;
      }
      
      while (this.position < this.text.length && this.text[this.position] >= '0' && this.text[this.position] <= '9') {
        this.position++;
      }
    }
    
    // Handle exponent
    if (this.position < this.text.length && (this.text[this.position] === 'e' || this.text[this.position] === 'E')) {
      this.position++;
      
      // Handle optional sign
      if (this.position < this.text.length && (this.text[this.position] === '+' || this.text[this.position] === '-')) {
        this.position++;
      }
      
      // Must have at least one digit
      if (this.position >= this.text.length || this.text[this.position] < '0' || this.text[this.position] > '9') {
        return false;
      }
      
      while (this.position < this.text.length && this.text[this.position] >= '0' && this.text[this.position] <= '9') {
        this.position++;
      }
    }
    
    return this.position > start;
  }
  
  private skipWhitespace(): void {
    while (this.position < this.text.length) {
      const char = this.text[this.position];
      if (char === ' ' || char === '\t' || char === '\n' || char === '\r') {
        this.position++;
      } else {
        break;
      }
    }
  }
}

// Enhanced function to clean text by removing JSON blocks with proper bracket matching
function removeJsonFromText(text: string): string {
  const parser = new BracketMatchingParser(text);
  let cleanText = text;
  
  // Remove code blocks first
  cleanText = cleanText.replace(/```(?:json)?\s*([\s\S]*?)\s*```/gi, (match, content) => {
    // Check if the content contains JSON-like structures we care about
    if (content.includes('recommendations') || content.includes('product_id') || content.includes('product_name')) {
      return ''; // Remove the entire code block
    }
    return match; // Keep non-JSON code blocks
  });
  
  // Remove standalone JSON objects and arrays
  let i = 0;
  while (i < cleanText.length) {
    const char = cleanText[i];
    
    if (char === '{') {
      const endPos = parser.findJsonObjectEnd(i);
      if (endPos !== null) {
        const jsonStr = cleanText.substring(i, endPos);
        
        // Check if this JSON contains recommendation data
        if (jsonStr.includes('recommendations') || jsonStr.includes('product_id') || jsonStr.includes('product_name')) {
          // Remove this JSON object
          cleanText = cleanText.substring(0, i) + cleanText.substring(endPos);
          // Don't increment i, re-process from the same position
          continue;
        } else {
          i = endPos;
        }
      } else {
        i++;
      }
    } else if (char === '[') {
      const endPos = parser.findJsonArrayEnd(i);
      if (endPos !== null) {
        const jsonStr = cleanText.substring(i, endPos);
        
        // Check if this array contains recommendation data
        if (jsonStr.includes('product_id') || jsonStr.includes('product_name')) {
          // Remove this JSON array
          cleanText = cleanText.substring(0, i) + cleanText.substring(endPos);
          // Don't increment i, re-process from the same position
          continue;
        } else {
          i = endPos;
        }
      } else {
        i++;
      }
    } else {
      i++;
    }
  }
  
  return cleanText.trim();
}


export interface UseWebSocketReturn {
  messages: ChatMessage[];
  isConnected: boolean;
  isConnecting: boolean;
  isWaitingForResponse: boolean;
  isUploading: boolean;
  sendMessage: (message: string, customerId?: string) => void;
  sendFiles: (files: File[], message?: string, customerId?: string) => Promise<void>;
  clearMessages: () => void;
  disconnect: () => void;
  userId: string;
}

export function useWebSocket(): UseWebSocketReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const hasConnected = useRef(false);

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages(prev => [...prev, message]);
  }, []);

  const handleWebSocketMessage = useCallback((response: WebSocketResponse) => {
    // Handle different response types - only show user and AI messages
    switch (response.type) {
      case 'chat': {
        const role = response.user_id === 'system' ? 'system' : 
                    response.user_id === 'assistant' ? 'ai' : 'user';
        
        // Only add if it's a user or AI message, not system
        if (role === 'user' || role === 'ai') {
          if (role === 'ai') {
            // AI response received - stop waiting for response
            setIsWaitingForResponse(false);
            
            // Check if message contains JSON recommendations as fallback
            const extractedProducts = extractRecommendationsFromText(response.message);
            
            // Remove JSON from the message text
            let cleanedText = removeJsonFromText(response.message);
            
            // If we extracted products, add a formatted list to the message
            if (extractedProducts && extractedProducts.length > 0) {
              const productList = extractedProducts
                .map(product => `• **${product.name}**: ${product.description}`)
                .join('\n');
              
              // Add the product list to cleaned text if there's remaining content
              if (cleanedText.trim()) {
                cleanedText = `${cleanedText}\n\n**Recommended Products:**\n${productList}`;
              } else {
                // If no other text, just show the products
                cleanedText = `**Here are my product recommendations:**\n\n${productList}`;
              }
            }
            
            // Regular AI message with cleaned text and extracted products
            addMessage({
              role: 'ai',
              text: cleanedText,
              products: extractedProducts || undefined,
              timestamp: new Date()
            });
          } else {
            // User message
            addMessage({
              role: 'user',
              text: response.message,
              timestamp: new Date()
            });
          }
        }
        break;
      }
      case 'stream': {
        // Handle streaming chunks from the assistant
        if (response.user_id === 'assistant') {
          setMessages(prev => {
            const lastMessage = prev[prev.length - 1];
            
            // If there's no current streaming message, or the last message isn't streaming, start a new one
            if (!lastMessage || lastMessage.role !== 'ai' || lastMessage.isStreaming !== true) {
              const rawText = response.message;
              
              // Filter streaming content to hide <results> tags during streaming
              const displayText = filterStreamingContent(rawText);
              
              return [
                ...prev,
                {
                  role: 'ai',
                  text: displayText,
                  rawText: rawText, // Store raw text separately for proper detection across chunks
                  isStreaming: true,
                  timestamp: new Date()
                }
              ];
            } else {
              // Append to existing streaming message
              // Use the accumulated raw text, not the display text
              const rawUpdatedText = (lastMessage.rawText || lastMessage.text || '') + response.message;
              
              // Filter streaming content to hide <results> tags during streaming
              const displayText = filterStreamingContent(rawUpdatedText);
              
              // Only clear loading state if we have meaningful content
              const meaningfulContent = displayText.trim();
              if (meaningfulContent && 
                  meaningfulContent.length > 5 && 
                  !meaningfulContent.startsWith('Using ') && 
                  !meaningfulContent.startsWith('Analyzing') &&
                  !meaningfulContent.startsWith('Searching') &&
                  !/^[.\s]*$/.test(meaningfulContent)) {
                setIsWaitingForResponse(false);
              }
              
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMessage,
                  text: displayText,
                  rawText: rawUpdatedText, // Keep accumulating raw text
                  isStreaming: true,
                  timestamp: new Date()
                }
              ];
            }
          });
        }
        break;
      }
      case 'chat_complete': {
        // Handle completion of streaming response - each completion is a separate message cycle
        if (response.user_id === 'assistant') {
          setMessages(prev => {
            const lastMessage = prev[prev.length - 1];
            
            // Extract products and clean text from the completed message
            const extractedProducts = extractRecommendationsFromText(response.message);
            let cleanedText = removeJsonFromText(response.message);
            
            // If we extracted products, add a formatted list to the message
            if (extractedProducts && extractedProducts.length > 0) {
              const productList = extractedProducts
                .map(product => `• **${product.name}**: ${product.description}`)
                .join('\n');
              
              // Add the product list to cleaned text if there's remaining content
              if (cleanedText.trim()) {
                cleanedText = `${cleanedText}\n\n**Recommended Products:**\n${productList}`;
              } else {
                // If no other text, just show the products
                cleanedText = `**Here are my product recommendations:**\n\n${productList}`;
              }
            }
            
            if (lastMessage && lastMessage.role === 'ai' && lastMessage.isStreaming) {
              // Complete the current streaming message with cleaned content
              return [
                ...prev.slice(0, -1),
                {
                  role: 'ai',
                  text: cleanedText,
                  products: extractedProducts || undefined,
                  isStreaming: false,
                  timestamp: new Date()
                }
              ];
            } else {
              // If there's no streaming message, create a new one (fallback case)
              return [
                ...prev,
                {
                  role: 'ai',
                  text: cleanedText,
                  products: extractedProducts || undefined,
                  isStreaming: false,
                  timestamp: new Date()
                }
              ];
            }
          });
        }
        break;
      }
      case 'message_boundary': {
        // Handle message boundary (when transferring to subagents/tools) - similar to chat_complete but doesn't end the conversation
        if (response.user_id === 'assistant') {
          setMessages(prev => {
            const lastMessage = prev[prev.length - 1];
            
            if (lastMessage && lastMessage.role === 'ai' && lastMessage.isStreaming) {
              // Just complete the current streaming message at the boundary, preserving its content
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMessage,
                  isStreaming: false,
                  timestamp: new Date()
                }
              ];
            } else if (response.message.trim()) {
              // If there's no streaming message but there's boundary content, create a new message
              return [
                ...prev,
                {
                  role: 'ai',
                  text: response.message,
                  isStreaming: false,
                  timestamp: new Date()
                }
              ];
            }
            // If no content, don't add a message
            return prev;
          });
        }
        break;
      }
      case 'structured_recommendations': {
        // Handle structured recommendations from the backend
        try {
          console.log('Received structured_recommendations:', response);
          
          // Parse the JSON from the message field
          const structuredData = JSON.parse(response.message) as { recommendations?: Recommendation[] };
          
          if (structuredData?.recommendations && Array.isArray(structuredData.recommendations)) {
            // Convert recommendations to Product format
            const products: Product[] = structuredData.recommendations.map((rec: Recommendation, index: number) => ({
              id: rec.product_id || rec.id || `structured-${index}`,
              name: rec.product_name || rec.name || 'Unknown Product',
              category: 'Recommended',
              price: 0,
              currency: 'USD',
              description: rec.reason || rec.description || 'No reason provided',
              stock_status: 'In Stock',
              confidence_score: rec.confidence_score || 0,
              similarity: rec.confidence_score ? rec.confidence_score / 10 : 0.5 // Convert to 0-1 scale for similarity
            }));
            
            // Stop waiting for response since we got structured data
            setIsWaitingForResponse(false);
            
            // Add structured product recommendations as a new AI message
            addMessage({
              role: 'ai',
              text: 'I\'ve updated the product recommendations on the right sidebar.',
              products,
              timestamp: new Date()
            });
          } else {
            console.warn('Invalid structured recommendations format:', structuredData);
          }
        } catch (error) {
          console.error('Error processing structured recommendations:', error);
          // Fallback: treat as regular message if JSON parsing fails
          addMessage({
            role: 'ai',
            text: response.message,
            timestamp: new Date()
          });
        }
        break;
      }
      case 'system':
        // Don't add system messages to chat, but keep loading state active if it's a tool usage message
        // Keep loading indicator active during tool operations
        if (response.message.includes('Using ') || response.message.includes('searching') || response.message.includes('Analyzing')) {
          // Don't clear loading state during tool operations
          // The loading will be cleared when actual content starts streaming
        }
        break;
      case 'error':
        // Don't add error messages to chat, just log them
        console.error('WebSocket error:', response.message);
        break;
      case 'file_saved':
        // Don't add file saved messages to chat
        break;
      default:
        console.warn('Unknown response type:', response.type);
    }
  }, [addMessage]);

  const handleConnectionChange = useCallback((connected: boolean) => {
    setIsConnected(connected);
    setIsConnecting(false);
  }, []);

  const sendMessage = useCallback((message: string, customerId?: string) => {
    if (!message.trim()) return;

    // Set loading state
    setIsWaitingForResponse(true);

    // Add user message to UI immediately
    addMessage({
      role: 'user',
      text: message,
      timestamp: new Date()
    });

    // Send via WebSocket with customer_id if provided
    websocketService.sendMessage(message, customerId);
  }, [addMessage]);

  const sendFiles = useCallback(async (files: File[], message?: string, customerId?: string) => {
    if (files.length === 0) return;

    try {
      // Set uploading state
      setIsUploading(true);
      setIsWaitingForResponse(true);

      // Convert files to base64
      const fileUploads: FileUpload[] = await Promise.all(
        Array.from(files).map(async (file) => ({
          filename: file.name,
          file_type: file.type,
          file_data: await WebSocketService.fileToBase64(file),
          size: file.size
        }))
      );

      // Add user message to UI if there's accompanying text
      if (message?.trim()) {
        addMessage({
          role: 'user',
          text: message,
          timestamp: new Date()
        });
      }

      // Add file upload message to UI
      const fileNames = files.map(f => f.name).join(', ');
      addMessage({
        role: 'user',
        text: `Uploaded files: ${fileNames}`,
        timestamp: new Date()
      });

      // Send via WebSocket with customer_id if provided
      websocketService.sendFiles(fileUploads, message, customerId);
      
      // Reset uploading state (but keep waiting for response)
      setIsUploading(false);
    } catch (error) {
      console.error('Error uploading files:', error);
      setIsUploading(false);
      setIsWaitingForResponse(false);
      // Don't add error message to chat, just log it
    }
  }, [addMessage]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setIsConnected(false);
    setIsConnecting(false);
    hasConnected.current = false; // Reset so connection can be re-established
  }, []);

  // Initialize WebSocket connection
  useEffect(() => {
    if (hasConnected.current) return;

    const initializeConnection = async () => {
      setIsConnecting(true);
      try {
        // Set up event handlers
        const unsubscribeMessage = websocketService.onMessage(handleWebSocketMessage);
        const unsubscribeConnection = websocketService.onConnectionChange(handleConnectionChange);

        // Connect
        await websocketService.connect();
        hasConnected.current = true;

        // Cleanup function
        return () => {
          unsubscribeMessage();
          unsubscribeConnection();
          websocketService.disconnect();
        };
      } catch (error) {
        console.error('Failed to connect to WebSocket:', error);
        setIsConnecting(false);
        // Don't add error message to chat, just log it
      }
    };

    const cleanup = initializeConnection();

    return () => {
      cleanup.then(cleanupFn => cleanupFn?.());
    };
  }, [handleConnectionChange, handleWebSocketMessage]); // Include dependencies used in the effect

  return {
    messages,
    isConnected,
    isConnecting,
    isWaitingForResponse,
    isUploading,
    sendMessage,
    sendFiles,
    clearMessages,
    disconnect,
    userId: websocketService.getUserId()
  };
}
