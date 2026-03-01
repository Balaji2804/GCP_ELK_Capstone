from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import sys
from datetime import datetime, timedelta
sys.path.append('/app/services')
from shared.logger import setup_logger
from shared.database import DatabaseClient

app = FastAPI(title="Analytics Service", version="1.0.0")
logger = setup_logger("analytics-service")

class AnalyticsEventRequest(BaseModel):
    event_type: str
    service_name: str
    user_id: Optional[str] = None
    metadata: dict = {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "analytics"}

@app.post("/events")
async def track_event(request: AnalyticsEventRequest):
    """Track an analytics event"""
    try:
        logger.info(f"Tracking event: {request.event_type} from {request.service_name}")
        db = DatabaseClient.get_client()

        event = db.table("analytics_events").insert({
            "event_type": request.event_type,
            "service_name": request.service_name,
            "user_id": request.user_id,
            "metadata": request.metadata
        }).execute()

        return {
            "event_id": event.data[0]['id'],
            "status": "tracked"
        }

    except Exception as e:
        logger.error(f"Error tracking event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/summary")
async def get_analytics_summary(days: int = 7):
    """Get analytics summary for the last N days"""
    try:
        db = DatabaseClient.get_client()

        since_date = (datetime.now() - timedelta(days=days)).isoformat()

        events = db.table("analytics_events").select("event_type, service_name").gte("created_at", since_date).execute()

        event_counts = {}
        service_counts = {}

        for event in events.data:
            event_type = event['event_type']
            service_name = event['service_name']

            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            service_counts[service_name] = service_counts.get(service_name, 0) + 1

        return {
            "period_days": days,
            "total_events": len(events.data),
            "event_counts": event_counts,
            "service_counts": service_counts
        }

    except Exception as e:
        logger.error(f"Error fetching analytics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/events")
async def get_events(event_type: Optional[str] = None, service_name: Optional[str] = None, limit: int = 100):
    """Get analytics events with optional filtering"""
    try:
        db = DatabaseClient.get_client()

        query = db.table("analytics_events").select("*").order("created_at", desc=True).limit(limit)

        if event_type:
            query = query.eq("event_type", event_type)

        if service_name:
            query = query.eq("service_name", service_name)

        events = query.execute()

        return {
            "count": len(events.data),
            "events": events.data
        }

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/user/{user_id}")
async def get_user_analytics(user_id: str, limit: int = 50):
    """Get analytics for a specific user"""
    try:
        db = DatabaseClient.get_client()

        events = db.table("analytics_events").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()

        event_timeline = {}
        for event in events.data:
            event_type = event['event_type']
            event_timeline[event_type] = event_timeline.get(event_type, 0) + 1

        return {
            "user_id": user_id,
            "total_events": len(events.data),
            "event_breakdown": event_timeline,
            "recent_events": events.data[:10]
        }

    except Exception as e:
        logger.error(f"Error fetching user analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
