from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import os
from typing import Optional
from pydantic import BaseModel
import sys
sys.path.append('/app/services')
from shared.logger import setup_logger
from shared.database import DatabaseClient
from shared.models import AnalyticsEvent

app = FastAPI(title="API Gateway", version="1.0.0")
logger = setup_logger("gateway-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOOKING_SERVICE_URL = os.getenv("BOOKING_SERVICE_URL", "http://booking-service:8001")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8005")

class ItineraryRequest(BaseModel):
    city: str
    interests: str
    user_email: str
    user_name: str

class BookingRequest(BaseModel):
    itinerary_id: str
    user_id: str
    payment_method: str

async def track_event(event_type: str, user_id: Optional[str], metadata: dict):
    """Track analytics event"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{ANALYTICS_SERVICE_URL}/events",
                json={
                    "event_type": event_type,
                    "service_name": "gateway-service",
                    "user_id": user_id,
                    "metadata": metadata
                },
                timeout=5.0
            )
    except Exception as e:
        logger.error(f"Failed to track event: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "gateway"}

@app.post("/api/itineraries")
async def create_itinerary(request: ItineraryRequest):
    """Create a new travel itinerary"""
    try:
        logger.info(f"Creating itinerary for {request.city}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BOOKING_SERVICE_URL}/itineraries",
                json={
                    "city": request.city,
                    "interests": request.interests,
                    "user_email": request.user_email,
                    "user_name": request.user_name
                },
                timeout=30.0
            )

            if response.status_code == 200:
                result = response.json()
                await track_event("itinerary_created", result.get("user_id"), {
                    "city": request.city,
                    "itinerary_id": result.get("itinerary_id")
                })
                return result
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

    except httpx.RequestError as e:
        logger.error(f"Error calling booking service: {e}")
        raise HTTPException(status_code=503, detail="Booking service unavailable")
    except Exception as e:
        logger.error(f"Error creating itinerary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bookings")
async def create_booking(request: BookingRequest):
    """Create a booking and process payment"""
    try:
        logger.info(f"Creating booking for itinerary {request.itinerary_id}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BOOKING_SERVICE_URL}/bookings",
                json={
                    "itinerary_id": request.itinerary_id,
                    "user_id": request.user_id,
                    "payment_method": request.payment_method
                },
                timeout=60.0
            )

            if response.status_code == 200:
                result = response.json()
                await track_event("booking_created", request.user_id, {
                    "booking_id": result.get("booking_id"),
                    "status": result.get("status")
                })
                return result
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

    except httpx.RequestError as e:
        logger.error(f"Error calling booking service: {e}")
        raise HTTPException(status_code=503, detail="Booking service unavailable")
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bookings/{booking_id}")
async def get_booking(booking_id: str):
    """Get booking details"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BOOKING_SERVICE_URL}/bookings/{booking_id}",
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

    except httpx.RequestError as e:
        logger.error(f"Error calling booking service: {e}")
        raise HTTPException(status_code=503, detail="Booking service unavailable")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
