from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import sys
import random
from decimal import Decimal
sys.path.append('/app/services')
from shared.logger import setup_logger
from shared.database import DatabaseClient

app = FastAPI(title="Fraud Detection Service", version="1.0.0")
logger = setup_logger("fraud-service")

class FraudCheckRequest(BaseModel):
    payment_id: str
    amount: str
    payment_method: str
    user_id: str

def calculate_risk_score(amount: Decimal, payment_method: str, user_id: str) -> tuple[Decimal, str, str]:
    """Calculate fraud risk score based on various factors"""
    risk_score = Decimal("0")
    reasons = []

    if amount > Decimal("1000"):
        risk_score += Decimal("30")
        reasons.append("High transaction amount")

    if payment_method == "new_card":
        risk_score += Decimal("20")
        reasons.append("New payment method")

    velocity_risk = random.randint(0, 25)
    risk_score += Decimal(str(velocity_risk))
    if velocity_risk > 15:
        reasons.append("High transaction velocity")

    ip_risk = random.randint(0, 15)
    risk_score += Decimal(str(ip_risk))
    if ip_risk > 10:
        reasons.append("Suspicious IP location")

    if risk_score > 70:
        status = "rejected"
    elif risk_score > 50:
        status = "manual_review"
    else:
        status = "approved"

    reason = ", ".join(reasons) if reasons else "No risk factors detected"

    return risk_score, status, reason

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "fraud"}

@app.post("/fraud-check")
async def check_fraud(request: FraudCheckRequest):
    """Perform fraud check on payment"""
    try:
        logger.info(f"Checking fraud for payment {request.payment_id}")
        db = DatabaseClient.get_client()

        risk_score, status, reason = calculate_risk_score(
            Decimal(request.amount),
            request.payment_method,
            request.user_id
        )

        fraud_check = db.table("fraud_checks").insert({
            "payment_id": request.payment_id,
            "risk_score": str(risk_score),
            "status": status,
            "reason": reason,
            "metadata": {
                "payment_method": request.payment_method,
                "amount": request.amount,
                "user_id": request.user_id
            }
        }).execute()

        fraud_check_id = fraud_check.data[0]['id']
        logger.info(f"Fraud check completed: {fraud_check_id}, Status: {status}, Risk Score: {risk_score}")

        return {
            "fraud_check_id": fraud_check_id,
            "risk_score": float(risk_score),
            "status": status,
            "reason": reason
        }

    except Exception as e:
        logger.error(f"Error performing fraud check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fraud-checks/{fraud_check_id}")
async def get_fraud_check(fraud_check_id: str):
    """Get fraud check details"""
    try:
        db = DatabaseClient.get_client()

        fraud_check = db.table("fraud_checks").select("*").eq("id", fraud_check_id).maybeSingle().execute()

        if not fraud_check.data:
            raise HTTPException(status_code=404, detail="Fraud check not found")

        return fraud_check.data

    except Exception as e:
        logger.error(f"Error fetching fraud check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
