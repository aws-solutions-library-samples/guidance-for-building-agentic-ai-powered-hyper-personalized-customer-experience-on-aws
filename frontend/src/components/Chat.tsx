import { useState, useRef, useEffect, useCallback } from 'react'
import { Upload, Send, Wifi, WifiOff, Mic, MicOff } from 'lucide-react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Card } from './ui/card'
import { ScrollArea } from './ui/scroll-area'
import { useNavigate } from 'react-router-dom'
import ProductCardBackend from './ProductCardBackend'
import MarkdownMessage from './MarkdownMessage'
import MedicalDisclaimer from './MedicalDisclaimer'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAppSelector } from '../store/hooks'
import Navbar from './Navbar'
import { getProductById } from '../utils/productUtils'
import { stripResultsTags } from '../utils/messageUtils'

// Extend the Window interface to include webkitSpeechRecognition
declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    webkitSpeechRecognition: any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    SpeechRecognition: any;
  }
}

// Type declarations for Speech Recognition API
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

interface SpeechRecognitionResultList {
  readonly length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  readonly length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
  readonly isFinal: boolean;
}

interface SpeechRecognitionAlternative {
  readonly transcript: string;
  readonly confidence: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
}

// Constants
const AUTO_SEND_DELAY = 100; // 100ms delay before auto-sending
const SPEECH_LANG = 'en-US';

function Chat() {
  const navigate = useNavigate();
  const [chatInput, setChatInput] = useState('');
  const chatBodyRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  
  // Medical disclaimer state
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  
  // Voice input states
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  // Get current customer from Redux store
  const currentCustomer = useAppSelector((state) => state.customers.current);
  
  // Use WebSocket hook for real-time chat
  const { 
    messages, 
    isConnected, 
    isConnecting, 
    isWaitingForResponse,
    sendMessage, 
    sendFiles, 
    disconnect,
    userId 
  } = useWebSocket();

  // Memoized handlers to prevent unnecessary re-renders
  const handleSendMessage = useCallback(async () => {
    if (!chatInput.trim()) return;
    
    const message = chatInput.trim();
    setChatInput('');
    
    // Send message with customer_id if user is logged in
    sendMessage(message, currentCustomer?.customer_id);
  }, [chatInput, sendMessage, currentCustomer]);

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    try {
      // Send files with customer_id if user is logged in
      await sendFiles(Array.from(files), undefined, currentCustomer?.customer_id);
    } catch (error) {
      console.error('Error uploading files:', error);
    }
    
    // Clear the input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [sendFiles, currentCustomer]);

  // Clear silence timer utility function
  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages]);

  // Show disclaimer on first visit to chat
  useEffect(() => {
    setShowDisclaimer(true);
  }, []);

  const handleCloseDisclaimer = useCallback(() => {
    setShowDisclaimer(false);
  }, []);


  // Check for speech recognition support on component mount
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSpeechSupported(true);
      recognitionRef.current = new SpeechRecognition();
      
      // Configure speech recognition
      if (recognitionRef.current) {
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;
        recognitionRef.current.lang = SPEECH_LANG;
        
        // Handle speech recognition results
        recognitionRef.current.onresult = (event: SpeechRecognitionEvent) => {
          let finalTranscript = '';
          let interimTranscript = '';
          
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += transcript;
            } else {
              interimTranscript += transcript;
            }
          }
          
          // Update chat input with interim results
          setChatInput(finalTranscript + interimTranscript);
          
            // If we have a final transcript, auto-send immediately
            if (finalTranscript.trim()) {
              stopListening();
              setTimeout(() => {
                // Send the final transcript directly instead of relying on state
                const message = finalTranscript.trim();
                setChatInput('');
                sendMessage(message, currentCustomer?.customer_id);
              }, AUTO_SEND_DELAY);
            }
        };
        
        // Handle speech recognition errors
        recognitionRef.current.onerror = (event: SpeechRecognitionErrorEvent) => {
          console.error('Speech recognition error:', event.error);
          setIsListening(false);
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
          }
        };
        
        // Handle speech recognition end
        recognitionRef.current.onend = () => {
          setIsListening(false);
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
          }
        };
      }
    }
    
    return () => {
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }
    };
  }, []);

  // Speech recognition control functions
  const startListening = useCallback(() => {
    if (!recognitionRef.current || !speechSupported || !isConnected) return;
    
    try {
      setChatInput(''); // Clear existing input
      setIsListening(true);
      recognitionRef.current.start();
    } catch (error) {
      console.error('Failed to start speech recognition:', error);
      setIsListening(false);
    }
  }, [speechSupported, isConnected]);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current || !isListening) return;
    
    try {
      setIsListening(false);
      recognitionRef.current.stop();
      clearSilenceTimer();
    } catch (error) {
      console.error('Failed to stop speech recognition:', error);
    }
  }, [isListening, clearSilenceTimer]);

  const toggleVoiceInput = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  // Memoized input event handlers
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setChatInput(e.target.value);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  }, [handleSendMessage]);

  const handleFileInputClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleNavigateHome = useCallback(() => {
    disconnect();
    navigate('/');
  }, [disconnect, navigate]);

  // Suggested queries for healthcare assistant
  const suggestedQueries = [
    {
      text: "I need help with joint pain relief",
      category: "Pain Management"
    },
    {
      text: "What vitamins should I take for better immunity?",
      category: "Vitamins & Supplements"
    },
    {
      text: "I have sensitive skin, what products are gentle?",
      category: "Skincare"
    },
    {
      text: "Help me build a first aid kit for my family",
      category: "First Aid"
    },
    {
      text: "I'm looking for natural sleep aids",
      category: "Sleep & Wellness"
    },
    {
      text: "What over-the-counter medications for allergies?",
      category: "Allergies"
    },
    {
      text: "I need products for managing diabetes",
      category: "Chronic Conditions"
    },
    {
      text: "What digestive health supplements do you recommend?",
      category: "Digestive Health"
    }
  ];

  // Handle clicking a suggested query
  const handleSuggestedQueryClick = useCallback((query: string) => {
    setChatInput(query);
    // Auto-send the message after a brief delay
    setTimeout(() => {
      sendMessage(query, currentCustomer?.customer_id);
      setChatInput('');
    }, 100);
  }, [sendMessage, currentCustomer]);

  // Loading messages to cycle through
  const loadingMessages = [
    "Finding recommendations...",
    "Analyzing your health profile...",
    "Searching product catalog...",
    "Matching products to your needs...",
    "Personalizing suggestions...",
    "Almost ready..."
  ];

  // State for cycling loading messages
  const [currentLoadingMessageIndex, setCurrentLoadingMessageIndex] = useState(0);

  // Effect to cycle through loading messages
  useEffect(() => {
    if (!isWaitingForResponse) return;

    const interval = setInterval(() => {
      setCurrentLoadingMessageIndex((prev) => (prev + 1) % loadingMessages.length);
    }, 2000); // Change message every 2 seconds

    return () => clearInterval(interval);
  }, [isWaitingForResponse, loadingMessages.length]);

  // Reset loading message index when starting new request
  useEffect(() => {
    if (isWaitingForResponse) {
      setCurrentLoadingMessageIndex(0);
    }
  }, [isWaitingForResponse]);

  // Memoized loading indicator component to prevent unnecessary re-renders
  const LoadingIndicator = useCallback(() => (
    <div className="flex justify-start">
      <Card className="bg-muted/50 border-0 p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
            <div className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
            <div className="w-2 h-2 bg-muted-foreground/60 rounded-full animate-bounce"></div>
          </div>
          <span className="text-sm text-muted-foreground transition-all duration-300">
            {loadingMessages[currentLoadingMessageIndex]}
          </span>
        </div>
      </Card>
    </div>
  ), [currentLoadingMessageIndex, loadingMessages]);

  const chatInputBar = (
    <div className="flex items-center gap-3 p-4 bg-background/80 backdrop-blur-sm border border-border/50 rounded-2xl shadow-sm">
      <input
        type="file"
        className="hidden"
        ref={fileInputRef}
        multiple
        onChange={handleFileUpload}
      />
      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9 rounded-full flex-shrink-0 hover:bg-muted/50"
        onClick={handleFileInputClick}
      >
        <Upload className="h-4 w-4" />
      </Button>
      
      {/* Voice Input Button */}
      {speechSupported && (
        <Button
          variant="ghost"
          size="icon"
          className={`h-9 w-9 rounded-full flex-shrink-0 transition-all duration-200 ${
            isListening 
              ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse' 
              : 'hover:bg-muted/50'
          }`}
          onClick={toggleVoiceInput}
          disabled={!isConnected}
          title={isListening ? 'Stop listening' : 'Start voice input'}
        >
          {isListening ? (
            <MicOff className="h-4 w-4" />
          ) : (
            <Mic className="h-4 w-4" />
          )}
        </Button>
      )}
      
      <Input
        type="text"
        placeholder={isListening ? "Listening... Speak now" : "Ask about health & wellness products..."}
        value={chatInput}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        className={`flex-1 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-sm transition-all duration-200 ${
          isListening ? 'text-red-600 placeholder:text-red-400' : ''
        }`}
        disabled={!isConnected}
      />
      <Button 
        size="icon"
        className="h-9 w-9 rounded-full flex-shrink-0"
        onClick={handleSendMessage}
        disabled={!isConnected}
      >
        <Send className="h-4 w-4" />
      </Button>
    </div>
  );

  // Right content for the navbar showing connection status
  const rightContent = (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {isConnecting ? (
          <>
            <WifiOff className="h-3 w-3 animate-pulse" />
            <span>Connecting...</span>
          </>
        ) : isConnected ? (
          <>
            <Wifi className="h-3 w-3 text-green-500" />
            <span>Connected</span>
          </>
        ) : (
          <>
            <WifiOff className="h-3 w-3 text-red-500" />
            <span>Disconnected</span>
          </>
        )}
      </div>
      <div className="text-xs text-muted-foreground font-mono">
        {userId.slice(0, 8)}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background">
      <div className="flex flex-col h-screen">
        {/* Header */}
        <Navbar
          showSearch={true}
          disableSearch={true}
          showBackButton={true}
          onBackClick={handleNavigateHome}
          onLogoClick={handleNavigateHome}
          rightContent={rightContent}
        />

        {/* Chat Container */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left 2/3 - Chat Messages */}
          <div className="flex flex-col relative overflow-hidden w-2/3">
            {messages.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8">
                <div className="text-center mb-8 max-w-2xl">
                  <h2 className="text-2xl font-semibold tracking-tight mb-3">
                    Your Personal Health Assistant
                  </h2>
                  <p className="text-muted-foreground leading-relaxed">
                    Get personalized product recommendations based on your health goals, 
                    medical history, and wellness preferences.
                  </p>
                </div>

                {/* Suggested Queries */}
                <div className="w-full max-w-3xl mb-8">
                  <div className="text-center mb-6">
                    <h3 className="text-sm font-medium text-muted-foreground mb-4">
                      Try asking me about:
                    </h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {suggestedQueries.map((query, index) => (
                      <Card
                        key={index}
                        className="p-4 cursor-pointer transition-all duration-200 hover:shadow-md hover:bg-muted/50 border border-border/50 group"
                        onClick={() => handleSuggestedQueryClick(query.text)}
                      >
                        <div className="text-left">
                          <div className="text-xs font-medium text-primary/70 mb-1 group-hover:text-primary transition-colors">
                            {query.category}
                          </div>
                          <div className="text-sm text-foreground group-hover:text-foreground/90 transition-colors">
                            {query.text}
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>

                <div className="w-full max-w-2xl px-4">
                  {chatInputBar}
                </div>
              </div>
            ) : (
              <>
                <ScrollArea 
                  className="flex-1 overflow-auto"
                  ref={chatBodyRef}
                >
                  <div className="p-6 pb-32">
                    <div className="flex flex-col gap-4 max-w-full">
                      {messages
                        .filter(msg => {
                          // Filter out messages that only contain products (no text)
                          // These will be shown in the sidebar instead
                          if (msg.role === 'ai' && msg.products && msg.products.length > 0 && !msg.text) {
                            return false;
                          }
                          return true;
                        })
                        .map((msg, i) => (
                        <div key={i}>
                          <div
                            className={`flex ${
                              msg.role === 'user' 
                                ? 'justify-end' 
                                : msg.role === 'system' 
                                  ? 'justify-center' 
                                  : 'justify-start'
                            }`}
                          >
                            <Card
                              className={`max-w-[85%] p-4 break-words overflow-hidden border-0 shadow-sm ${
                                msg.role === 'user'
                                  ? 'bg-primary text-primary-foreground'
                                  : msg.role === 'system'
                                    ? 'bg-muted/50 border border-border/50'
                                    : 'bg-muted/30'
                              }`}
                            >
                              {msg.text && (
                                <>
                                  {msg.role === 'ai' ? (
                                    <MarkdownMessage content={stripResultsTags(msg.text)} />
                                  ) : (
                                    <p className={`text-sm break-words leading-relaxed ${
                                      msg.role === 'system' ? 'text-center text-muted-foreground' : ''
                                    }`}>
                                      {msg.text}
                                    </p>
                                  )}
                                </>
                              )}
                              {msg.product && (
                                <div className="mt-3">
                                  <ProductCardBackend product={msg.product} />
                                </div>
                              )}
                            </Card>
                          </div>
                        </div>
                      ))}
                      
                      {/* Loading indicator */}
                      {isWaitingForResponse && <LoadingIndicator />}
                    </div>
                  </div>
                </ScrollArea>
                
                {/* Fixed Chat Input Bar */}
                <div className="absolute bottom-0 left-0 right-0 p-6 bg-background/95 backdrop-blur-sm border-t border-border/50">
                  <div className="max-w-full">
                    {chatInputBar}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Right 1/3 - Featured Products */}
          <div className="flex flex-col border-l border-border/50 bg-muted/20 overflow-hidden w-1/3">
            <div className="p-4 border-b border-border/50 flex-shrink-0">
              <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                Featured Products
              </h3>
            </div>
            <ScrollArea className="flex-1 overflow-auto">
              <div className="p-4">
                <div className="flex flex-col gap-4">
                  {/* Check if we have chat recommendations */}
                  {messages.filter(msg => msg.products && msg.products.length > 0).length > 0 ? (
                    /* Show chat recommendations */
                    messages
                      .filter(msg => msg.products && msg.products.length > 0)
                      .flatMap(msg => msg.products!)
                      .slice(0, 20) // Limit to first 20 products
                      .map((product, index) => {
                        // Use getProductById to get standardized product attributes
                        const standardizedProduct = getProductById(product.id);
                        // If product found in catalog, use it; otherwise use fallbacks
                        const productWithDefaults = standardizedProduct ? {
                          ...product,
                          ...standardizedProduct,
                          // Preserve any additional fields from the AI response
                          similarity: product.similarity
                        } : {
                          ...product,
                          image_url: product.image_url || `/images/${product.id}.png`,
                          price: typeof product.price === 'number' ? product.price : 0,
                          currency: product.currency || 'USD',
                          stock_status: product.stock_status || 'In Stock',
                          category: product.category || 'Health & Wellness',
                          rating: typeof product.rating === 'number' ? product.rating : 4.0,
                          reviews_count: typeof product.reviews_count === 'number' ? product.reviews_count : 0
                        };
                        
                        return (
                          <div key={`${product.id}-${index}`} className="w-full">
                            <ProductCardBackend 
                              product={productWithDefaults} 
                              showSimilarity={product.similarity !== undefined}
                              isRecommendation={true}
                            />
                          </div>
                        );
                      })
                  ) : (
                    /* Show default featured products from home page */
                    <>
                      {/* Info message */}
                      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 mb-4">
                        <p className="text-xs text-blue-700 dark:text-blue-300 text-center">
                          These products will update with personalized recommendations as you chat
                        </p>
                      </div>
                      
                      {/* Default featured products */}
                      {[
                        {
                          id: 'VIT001',
                          name: 'Premium Vitamin D3 5000 IU',
                          brand: 'WellnessPlus',
                          price: 24.99,
                          currency: 'USD',
                          description: 'High-potency vitamin D3 supplement for bone health and immune support',
                          category: 'Vitamins',
                          stock_status: 'In Stock',
                          rating: 4.7,
                          reviews: 1247,
                          image_url: '/images/VIT001.png'
                        },
                        {
                          id: 'SKIN001',
                          name: 'Hyaluronic Acid Serum',
                          brand: 'DermaCare',
                          price: 34.99,
                          currency: 'USD',
                          description: 'Advanced anti-aging serum with hyaluronic acid for hydrated, youthful skin',
                          category: 'Skincare',
                          stock_status: 'In Stock',
                          rating: 4.6,
                          reviews: 1834,
                          image_url: '/images/SKIN001.png'
                        },
                        {
                          id: 'OTC001',
                          name: 'Ibuprofen 200mg Tablets',
                          brand: 'PainRelief Plus',
                          price: 12.99,
                          currency: 'USD',
                          description: 'Fast-acting pain relief for headaches, muscle aches, and inflammation',
                          category: 'Medicine',
                          stock_status: 'In Stock',
                          rating: 4.5,
                          reviews: 1456,
                          image_url: '/images/OTC001.png'
                        },
                        {
                          id: 'FIRST001',
                          name: 'First Aid Kit Complete',
                          brand: 'SafetyFirst',
                          price: 29.99,
                          currency: 'USD',
                          description: 'Comprehensive first aid kit with essential medical supplies for emergencies',
                          category: 'First Aid',
                          stock_status: 'In Stock',
                          rating: 4.7,
                          reviews: 1876,
                          image_url: '/images/FIRST001.png'
                        }
                      ].map((product) => (
                        <div key={product.id} className="w-full">
                          <ProductCardBackend product={product} />
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
      
      {/* Medical Disclaimer Dialog */}
      <MedicalDisclaimer 
        isOpen={showDisclaimer} 
        onClose={handleCloseDisclaimer} 
      />
    </div>
  );
}

export default Chat;
