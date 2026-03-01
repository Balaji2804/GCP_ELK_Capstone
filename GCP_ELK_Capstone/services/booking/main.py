from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import sys
from decimal import Decimal
from typing import Optional
sys.path.append('/app/services')
from shared.logger import setup_logger
from shared.database import DatabaseClient
from shared.message_broker import MessageBroker

app = FastAPI(title="Booking Service", version="1.0.0")
logger = setup_logger("booking-service")

PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8002")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class ItineraryRequest(BaseModel):
    city: str
    interests: str
    user_email: str
    user_name: str

class BookingRequest(BaseModel):
    itinerary_id: str
    user_id: str
    payment_method: str

def generate_itinerary_with_llm(city: str, interests: str) -> str:
    """Generate itinerary using Groq LLM"""
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate

    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile",
        temperature=0.3
    )

    itinerary_prompt = ChatPromptTemplate([
        ("system", "You are a helpful travel assistant. Create a day trip itinerary for {city} based on user's interest: {interests}. Provide a brief, bulleted itinerary"),
        ("human", "Create an itinerary for my day trip")
    ])

    response = llm.invoke(
        itinerary_prompt.format_messages(city=city, interests=interests)
    )

    return response.content

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "booking"}

@app.post("/itineraries")
async def create_itinerary(request: ItineraryRequest):
    """Create a new itinerary"""
    try:
        logger.info(f"Creating itinerary for {request.city}")
        db = DatabaseClient.get_client()

        user_response = db.table("users").select("*").eq("email", request.user_email).maybeSingle().execute()

        if user_response.data:
            user = user_response.data
            user_id = user['id']
        else:
            user_insert = db.table("users").insert({
                "email": request.user_email,
                "full_name": request.user_name
            }).execute()
            user_id = user_insert.data[0]['id']

        interests_list = [i.strip() for i in request.interests.split(",")]
        itinerary_content = generate_itinerary_with_llm(request.city, request.interests)

        itinerary = db.table("itineraries").insert({
            "user_id": user_id,
            "city": request.city,
            "interests": interests_list,
            "content": itinerary_content,
            "status": "draft"
        }).execute()

        logger.info(f"Itinerary created: {itinerary.data[0]['id']}")

        return {
            "itinerary_id": itinerary.data[0]['id'],
            "user_id": user_id,
            "city": request.city,
            "content": itinerary_content,
            "status": "draft"
        }

    except Exception as e:
        logger.error(f"Error creating itinerary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bookings")
async def create_booking(request: BookingRequest):
    """Create a booking and initiate payment"""
    try:
        logger.info(f"Creating booking for itinerary {request.itinerary_id}")
        db = DatabaseClient.get_client()

        itinerary = db.table("itineraries").select("*").eq("id", request.itinerary_id).maybeSingle().execute()
        if not itinerary.data:
            raise HTTPException(status_code=404, detail="Itinerary not found")

        total_amount = Decimal("299.99")

        booking = db.table("bookings").insert({
            "itinerary_id": request.itinerary_id,
            "user_id": request.user_id,
            "total_amount": str(total_amount),
            "status": "pending"
        }).execute()

        booking_id = booking.data[0]['id']
        logger.info(f"Booking created: {booking_id}")

        async with httpx.AsyncClient() as client:
            payment_response = await client.post(
                f"{PAYMENT_SERVICE_URL}/payments",
                json={
                    "booking_id": booking_id,
                    "amount": str(total_amount),
                    "payment_method": request.payment_method,
                    "user_id": request.user_id
                },
                timeout=60.0
            )

            if payment_response.status_code == 200:
                payment_data = payment_response.json()

                db.table("bookings").update({
                    "payment_id": payment_data['payment_id'],
                    "status": payment_data['status']
                }).eq("id", booking_id).execute()

                db.table("itineraries").update({
                    "status": "booked" if payment_data['status'] == 'confirmed' else "draft"
                }).eq("id", request.itinerary_id).execute()

                return {
                    "booking_id": booking_id,
                    "payment_id": payment_data['payment_id'],
                    "status": payment_data['status'],
                    "fraud_check": payment_data.get('fraud_check')
                }
            else:
                db.table("bookings").update({"status": "failed"}).eq("id", booking_id).execute()
                raise HTTPException(status_code=payment_response.status_code, detail="Payment failed")

    except httpx.RequestError as e:
        logger.error(f"Error calling payment service: {e}")
        raise HTTPException(status_code=503, detail="Payment service unavailable")
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: str):
    """Get booking details"""
    try:
        db = DatabaseClient.get_client()

        booking = db.table("bookings").select("*, itineraries(*), payments(*)").eq("id", booking_id).maybeSingle().execute()

        if not booking.data:
            raise HTTPException(status_code=404, detail="Booking not found")

        return booking.data

    except Exception as e:
        logger.error(f"Error fetching booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
