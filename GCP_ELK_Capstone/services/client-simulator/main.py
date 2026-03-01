import httpx
import asyncio
import random
import os
import sys
from datetime import datetime
sys.path.append('/app/services')
from shared.logger import setup_logger

logger = setup_logger("client-simulator")

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway-service:8000")

CITIES = [
    "Paris", "Tokyo", "New York", "London", "Dubai",
    "Barcelona", "Rome", "Sydney", "Bangkok", "Singapore"
]

INTERESTS = [
    ["museums", "art", "history"],
    ["food", "restaurants", "nightlife"],
    ["beaches", "nature", "hiking"],
    ["shopping", "fashion", "culture"],
    ["adventure", "sports", "outdoor"],
    ["photography", "architecture", "sightseeing"]
]

PAYMENT_METHODS = ["credit_card", "debit_card", "new_card", "paypal"]

async def simulate_user_journey(user_id: int):
    """Simulate a complete user journey from itinerary creation to booking"""
    try:
        city = random.choice(CITIES)
        interests = random.choice(INTERESTS)
        payment_method = random.choice(PAYMENT_METHODS)

        user_email = f"user{user_id}@example.com"
        user_name = f"Test User {user_id}"

        logger.info(f"User {user_id} starting journey for {city}")

        async with httpx.AsyncClient() as client:
            logger.info(f"User {user_id} creating itinerary for {city}")
            itinerary_response = await client.post(
                f"{GATEWAY_URL}/api/itineraries",
                json={
                    "city": city,
                    "interests": ", ".join(interests),
                    "user_email": user_email,
                    "user_name": user_name
                },
                timeout=60.0
            )

            if itinerary_response.status_code == 200:
                itinerary_data = itinerary_response.json()
                itinerary_id = itinerary_data['itinerary_id']
                user_db_id = itinerary_data['user_id']
                logger.info(f"User {user_id} created itinerary: {itinerary_id}")

                await asyncio.sleep(random.uniform(1, 3))

                should_book = random.random() > 0.3
                if should_book:
                    logger.info(f"User {user_id} creating booking for itinerary {itinerary_id}")
                    booking_response = await client.post(
                        f"{GATEWAY_URL}/api/bookings",
                        json={
                            "itinerary_id": itinerary_id,
                            "user_id": user_db_id,
                            "payment_method": payment_method
                        },
                        timeout=90.0
                    )

                    if booking_response.status_code == 200:
                        booking_data = booking_response.json()
                        logger.info(f"User {user_id} completed booking: {booking_data['booking_id']}, Status: {booking_data['status']}")
                    else:
                        logger.warning(f"User {user_id} booking failed: {booking_response.status_code}")
                else:
                    logger.info(f"User {user_id} decided not to book")
            else:
                logger.error(f"User {user_id} itinerary creation failed: {itinerary_response.status_code}")

    except Exception as e:
        logger.error(f"Error in user {user_id} journey: {e}")

async def run_simulation(num_users: int, concurrent: int):
    """Run simulation with specified number of users"""
    logger.info(f"Starting simulation with {num_users} users, {concurrent} concurrent")

    tasks = []
    for i in range(num_users):
        tasks.append(simulate_user_journey(i))

        if len(tasks) >= concurrent:
            await asyncio.gather(*tasks)
            tasks = []
            await asyncio.sleep(random.uniform(0.5, 2))

    if tasks:
        await asyncio.gather(*tasks)

    logger.info("Simulation completed")

async def continuous_simulation():
    """Run continuous simulation"""
    logger.info("Starting continuous simulation mode")

    iteration = 0
    while True:
        iteration += 1
        logger.info(f"Starting iteration {iteration}")

        num_users = random.randint(3, 10)
        concurrent = min(num_users, 3)

        await run_simulation(num_users, concurrent)

        wait_time = random.uniform(10, 30)
        logger.info(f"Waiting {wait_time:.1f} seconds before next iteration")
        await asyncio.sleep(wait_time)

if __name__ == "__main__":
    mode = os.getenv("SIMULATION_MODE", "continuous")

    if mode == "continuous":
        asyncio.run(continuous_simulation())
    else:
        num_users = int(os.getenv("NUM_USERS", "10"))
        concurrent = int(os.getenv("CONCURRENT_USERS", "3"))
        asyncio.run(run_simulation(num_users, concurrent))
