from fastapi import FastAPI
import os
import sys
import threading
sys.path.append('/app/services')
from shared.logger import setup_logger
from shared.database import DatabaseClient
from shared.message_broker import MessageBroker

app = FastAPI(title="Notification Service", version="1.0.0")
logger = setup_logger("notification-service")

def send_notification(notification_data: dict):
    """Simulate sending notification via email/sms/push"""
    try:
        db = DatabaseClient.get_client()

        notification_type = notification_data.get('type', 'email')
        user_id = notification_data.get('user_id')

        if notification_type == 'payment_success':
            subject = "Payment Successful"
            message = f"Your payment of ${notification_data.get('amount')} has been processed successfully. Booking ID: {notification_data.get('booking_id')}"
        elif notification_type == 'payment_failed_fraud':
            subject = "Payment Failed"
            message = f"Your payment was declined due to: {notification_data.get('reason')}. Please contact support."
        elif notification_type == 'booking_confirmed':
            subject = "Booking Confirmed"
            message = f"Your travel booking has been confirmed. Booking ID: {notification_data.get('booking_id')}"
        else:
            subject = "Notification"
            message = notification_data.get('message', 'You have a new notification')

        notification = db.table("notifications").insert({
            "user_id": user_id,
            "type": "email",
            "channel": notification_type.split('_')[0] if '_' in notification_type else "general",
            "subject": subject,
            "message": message,
            "status": "sent"
        }).execute()

        logger.info(f"Notification sent: {notification.data[0]['id']}")

    except Exception as e:
        logger.error(f"Error sending notification: {e}")

def consume_notifications():
    """Consume notification messages from queue"""
    try:
        broker = MessageBroker()
        broker.declare_queue("notifications")
        logger.info("Starting notification consumer")
        broker.consume("notifications", send_notification)
    except Exception as e:
        logger.error(f"Error in notification consumer: {e}")

@app.on_event("startup")
async def startup_event():
    """Start the notification consumer in a background thread"""
    consumer_thread = threading.Thread(target=consume_notifications, daemon=True)
    consumer_thread.start()
    logger.info("Notification service started")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "notification"}

@app.get("/notifications/{user_id}")
async def get_user_notifications(user_id: str):
    """Get all notifications for a user"""
    try:
        db = DatabaseClient.get_client()

        notifications = db.table("notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()

        return {
            "user_id": user_id,
            "notifications": notifications.data
        }

    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
