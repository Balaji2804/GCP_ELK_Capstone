from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import sys
from decimal import Decimal
sys.path.append('/app/services')
from shared.logger import setup_logger
from shared.database import DatabaseClient
from shared.message_broker import MessageBroker

app = FastAPI(title="Payment Service", version="1.0.0")
logger = setup_logger("payment-service")

FRAUD_SERVICE_URL = os.getenv("FRAUD_SERVICE_URL", "http://fraud-service:8003")

class PaymentRequest(BaseModel):
    booking_id: str
    amount: str
    payment_method: str
    user_id: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "payment"}

@app.post("/payments")
async def process_payment(request: PaymentRequest):
    """Process payment and check for fraud"""
    try:
        logger.info(f"Processing payment for booking {request.booking_id}")
        db = DatabaseClient.get_client()

        payment = db.table("payments").insert({
            "booking_id": request.booking_id,
            "amount": request.amount,
            "payment_method": request.payment_method,
            "status": "processing",
            "currency": "USD"
        }).execute()

        payment_id = payment.data[0]['id']
        logger.info(f"Payment created: {payment_id}")

        async with httpx.AsyncClient() as client:
            fraud_response = await client.post(
                f"{FRAUD_SERVICE_URL}/fraud-check",
                json={
                    "payment_id": payment_id,
                    "amount": request.amount,
                    "payment_method": request.payment_method,
                    "user_id": request.user_id
                },
                timeout=30.0
            )

            if fraud_response.status_code == 200:
                fraud_data = fraud_response.json()

                if fraud_data['status'] == 'approved':
                    db.table("payments").update({
                        "status": "completed",
                        "fraud_check_id": fraud_data['fraud_check_id']
                    }).eq("id", payment_id).execute()

                    try:
                        broker = MessageBroker()
                        broker.declare_queue("notifications")
                        broker.publish("notifications", {
                            "type": "payment_success",
                            "user_id": request.user_id,
                            "booking_id": request.booking_id,
                            "payment_id": payment_id,
                            "amount": request.amount
                        })
                        broker.close()
                    except Exception as e:
                        logger.error(f"Failed to send notification message: {e}")

                    return {
                        "payment_id": payment_id,
                        "status": "confirmed",
                        "fraud_check": fraud_data
                    }
                else:
                    db.table("payments").update({
                        "status": "failed",
                        "fraud_check_id": fraud_data['fraud_check_id']
                    }).eq("id", payment_id).execute()

                    try:
                        broker = MessageBroker()
                        broker.declare_queue("notifications")
                        broker.publish("notifications", {
                            "type": "payment_failed_fraud",
                            "user_id": request.user_id,
                            "booking_id": request.booking_id,
                            "payment_id": payment_id,
                            "reason": fraud_data.get('reason', 'Fraud detected')
                        })
                        broker.close()
                    except Exception as e:
                        logger.error(f"Failed to send notification message: {e}")

                    raise HTTPException(status_code=400, detail=f"Payment rejected: {fraud_data.get('reason', 'Fraud detected')}")
            else:
                db.table("payments").update({"status": "failed"}).eq("id", payment_id).execute()
                raise HTTPException(status_code=fraud_response.status_code, detail="Fraud check failed")

    except httpx.RequestError as e:
        logger.error(f"Error calling fraud service: {e}")
        raise HTTPException(status_code=503, detail="Fraud service unavailable")
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    """Get payment details"""
    try:
        db = DatabaseClient.get_client()

        payment = db.table("payments").select("*, fraud_checks(*)").eq("id", payment_id).maybeSingle().execute()

        if not payment.data:
            raise HTTPException(status_code=404, detail="Payment not found")

        return payment.data

    except Exception as e:
        logger.error(f"Error fetching payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
