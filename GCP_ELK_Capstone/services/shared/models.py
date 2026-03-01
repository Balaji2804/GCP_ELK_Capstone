from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class User(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    full_name: str
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Itinerary(BaseModel):
    id: Optional[str] = None
    user_id: str
    city: str
    interests: List[str] = []
    content: str
    status: str = "draft"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Booking(BaseModel):
    id: Optional[str] = None
    itinerary_id: str
    user_id: str
    status: str = "pending"
    total_amount: Decimal
    payment_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Payment(BaseModel):
    id: Optional[str] = None
    booking_id: str
    amount: Decimal
    currency: str = "USD"
    status: str = "pending"
    payment_method: str
    fraud_check_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FraudCheck(BaseModel):
    id: Optional[str] = None
    payment_id: str
    risk_score: Decimal
    status: str = "approved"
    reason: Optional[str] = None
    checked_at: Optional[datetime] = None
    metadata: dict = {}

class Notification(BaseModel):
    id: Optional[str] = None
    user_id: str
    type: str  # email, sms, push
    channel: str  # booking, payment, general
    subject: str
    message: str
    status: str = "pending"
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

class AnalyticsEvent(BaseModel):
    id: Optional[str] = None
    event_type: str
    service_name: str
    user_id: Optional[str] = None
    metadata: dict = {}
    created_at: Optional[datetime] = None
