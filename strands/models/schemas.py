from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, EmailStr
import uuid

# Base Models
class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

# Address Model
class Address(BaseModel):
    """Customer address model"""
    street: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=50)
    zip_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=1, max_length=50)

# Personal Info Model
class PersonalInfo(BaseModel):
    """Customer personal information model"""
    name: str = Field(..., min_length=1, max_length=100)
    gender: str = Field(..., min_length=1, max_length=20)
    email: EmailStr
    address: Address
    age: Optional[int] = Field(None, ge=0, le=150)
    date_of_birth: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    occupation: Optional[str] = Field(None, max_length=100)
    lifestyle: Optional[str] = Field(None, max_length=50)
    fitness_level: Optional[str] = Field(None, max_length=50)
    dietary_preferences: Optional[List[str]] = Field(default_factory=list)
    allergies: Optional[List[str]] = Field(default_factory=list)
    medications: Optional[List[str]] = Field(default_factory=list)
    health_goals: Optional[List[str]] = Field(default_factory=list)

# Body Composition Model
class BodyComposition(BaseModel):
    """Customer body composition data"""
    height: Optional[str] = None
    height_cm: Optional[float] = None
    weight: Optional[str] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    muscle_mass_percentage: Optional[float] = None
    bone_density: Optional[str] = None
    metabolic_rate: Optional[int] = None
    waist_circumference: Optional[str] = None
    blood_pressure: Optional[str] = None
    resting_heart_rate: Optional[int] = None
    last_measured: Optional[str] = None

# Bloodwork Data Model
class BloodworkData(BaseModel):
    """Customer bloodwork data"""
    test_date: Optional[str] = None
    lab_provider: Optional[str] = None
    complete_blood_count: Optional[Dict[str, Any]] = Field(default_factory=dict)
    comprehensive_metabolic_panel: Optional[Dict[str, Any]] = Field(default_factory=dict)
    lipid_panel: Optional[Dict[str, Any]] = Field(default_factory=dict)
    vitamins_minerals: Optional[Dict[str, Any]] = Field(default_factory=dict)
    hormones: Optional[Dict[str, Any]] = Field(default_factory=dict)
    inflammatory_markers: Optional[Dict[str, Any]] = Field(default_factory=dict)
    women_specific: Optional[Dict[str, Any]] = Field(default_factory=dict)
    diabetes_markers: Optional[Dict[str, Any]] = Field(default_factory=dict)
    cardiac_markers: Optional[Dict[str, Any]] = Field(default_factory=dict)
    kidney_function: Optional[Dict[str, Any]] = Field(default_factory=dict)

# Order History Item Model
class OrderHistoryItem(BaseModel):
    """Individual order in customer's history"""
    order_id: str
    order_date: str
    total_amount: float
    status: str
    items: List[Dict[str, Any]] = Field(default_factory=list)
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = None

# Purchase Patterns Model
class PurchasePatterns(BaseModel):
    """Customer purchase pattern analysis"""
    total_orders: Optional[int] = 0
    total_spent: Optional[float] = 0.0
    average_order_value: Optional[float] = 0.0
    favorite_categories: Optional[List[str]] = Field(default_factory=list)
    purchase_frequency: Optional[str] = None
    preferred_brands: Optional[List[str]] = Field(default_factory=list)
    seasonal_trends: Optional[str] = None

# Health Insights Model
class HealthInsights(BaseModel):
    """Customer health insights and recommendations"""
    risk_factors: Optional[List[str]] = Field(default_factory=list)
    recommendations: Optional[List[str]] = Field(default_factory=list)
    health_score: Optional[int] = Field(None, ge=0, le=100)
    last_health_assessment: Optional[str] = None

# Customer Models
class Customer(BaseModel):
    """Customer data model - requires customer_id, name, gender, email, address"""
    customer_id: str = Field(..., min_length=1, max_length=50)
    personal_info: PersonalInfo
    body_composition: Optional[BodyComposition] = None
    bloodwork_data: Optional[BloodworkData] = None
    order_history: Optional[List[OrderHistoryItem]] = Field(default_factory=list)
    purchase_patterns: Optional[PurchasePatterns] = None
    health_insights: Optional[HealthInsights] = None
    
    # Computed properties for backward compatibility and easy access to required fields
    @property
    def name(self) -> str:
        return self.personal_info.name
    
    @property
    def gender(self) -> str:
        return self.personal_info.gender
    
    @property
    def email(self) -> str:
        return self.personal_info.email
    
    @property
    def address(self) -> Address:
        return self.personal_info.address

# Simplified Customer Creation Model for minimal required fields
class CustomerCreateMinimal(BaseModel):
    """Minimal customer creation with only required fields"""
    customer_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    gender: str = Field(..., min_length=1, max_length=20)
    email: EmailStr
    address: Address
    
    def to_full_customer(self) -> Customer:
        """Convert minimal customer to full customer model"""
        personal_info = PersonalInfo(
            name=self.name,
            gender=self.gender,
            email=self.email,
            address=self.address
        )
        return Customer(
            customer_id=self.customer_id,
            personal_info=personal_info
        )

class CustomerCreate(Customer):
    """Customer creation model"""
    pass

class CustomerResponse(Customer, TimestampMixin):
    """Customer response model"""
    pass

# Search Models
class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, max_length=500)
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    size: Optional[int] = Field(default=10, ge=1, le=100)
    from_: Optional[int] = Field(default=0, ge=0, alias="from")

class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    total_hits: int
    results: List[Dict[str, Any]]
    from_: int = Field(alias="from")
    size: int
    took_ms: Optional[float] = None

class SemanticSearchRequest(SearchRequest):
    """Semantic search request model"""
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

# Personalization Models (for future implementation)
# class PersonalizationRequest(BaseModel):
#     """Personalization request model"""
#     customer_id: str
#     query: Optional[str] = None
#     max_results: int = Field(default=10, ge=1, le=50)

# class PersonalizationResponse(BaseModel):
#     """Personalization response model"""
#     customer_id: str
#     recommendations: List[Dict[str, Any]]
#     personalization_score: float = Field(..., ge=0.0, le=1.0)
#     reasoning: List[str] = Field(default_factory=list)
#     timestamp: datetime = Field(default_factory=datetime.now)

# API Response Models
class APIResponse(BaseModel):
    """Generic API response model"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# Health Check Models
class HealthCheck(BaseModel):
    """Health check response model"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    services: Dict[str, str] = Field(default_factory=dict)

# WebSocket Models
class FileUpload(BaseModel):
    """File upload model for WebSocket"""
    filename: str
    file_type: str
    file_data: str  # base64 encoded
    size: Optional[int] = None

class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    type: str = Field(..., description="Message type: 'chat', 'file_upload', 'system'")
    message: Optional[str] = None
    files: Optional[List[FileUpload]] = Field(default_factory=list)
    user_id: str
    customer_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class WebSocketResponse(BaseModel):
    """WebSocket response model"""
    type: str = Field(..., description="Response type: 'chat', 'stream', 'chat_complete', 'message_boundary', 'system', 'error', 'file_saved', 'structured_recommendations'")
    message: str
    data: Optional[Dict[str, Any]] = None
    user_id: str = "system"
    timestamp: datetime = Field(default_factory=datetime.now)

class Product(BaseModel):
    """Product"""
    product_id: str
    product_name: str
    reason: str
    confidence_score: int

class Recommendations(BaseModel):
    """Recommendations"""
    recommendations: List[Product] = Field(default_factory=list)