import streamlit as st
import httpx
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Enterprise Travel Booking",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway-service:8000")

if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'current_itinerary' not in st.session_state:
    st.session_state.current_itinerary = None
if 'booking_history' not in st.session_state:
    st.session_state.booking_history = []

def create_itinerary(city: str, interests: str, user_email: str, user_name: str):
    """Create a new itinerary via Gateway API"""
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{GATEWAY_URL}/api/itineraries",
                json={
                    "city": city,
                    "interests": interests,
                    "user_email": user_email,
                    "user_name": user_name
                }
            )
            if response.status_code == 200:
                return response.json(), None
            else:
                return None, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

def create_booking(itinerary_id: str, user_id: str, payment_method: str):
    """Create a booking via Gateway API"""
    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                f"{GATEWAY_URL}/api/bookings",
                json={
                    "itinerary_id": itinerary_id,
                    "user_id": user_id,
                    "payment_method": payment_method
                }
            )
            if response.status_code == 200:
                return response.json(), None
            else:
                return None, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

def get_booking_details(booking_id: str):
    """Get booking details via Gateway API"""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{GATEWAY_URL}/api/bookings/{booking_id}")
            if response.status_code == 200:
                return response.json(), None
            else:
                return None, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

st.title("✈️ Enterprise Travel Booking Platform")
st.markdown("**AI-Powered Itinerary Planning with Secure Payment Processing**")

with st.sidebar:
    st.header("User Profile")

    if not st.session_state.user_email:
        with st.form("user_form"):
            st.subheader("Welcome!")
            user_email = st.text_input("Email Address", placeholder="user@example.com")
            user_name = st.text_input("Full Name", placeholder="John Doe")
            login_btn = st.form_submit_button("Continue")

            if login_btn and user_email and user_name:
                st.session_state.user_email = user_email
                st.session_state.user_name = user_name
                st.rerun()
    else:
        st.success(f"Logged in as: **{st.session_state.user_email}**")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

        st.divider()
        st.subheader("Quick Stats")
        st.metric("Total Bookings", len(st.session_state.booking_history))
        if st.session_state.current_itinerary:
            st.info("Active itinerary ready for booking")

if not st.session_state.user_email:
    st.info("Please enter your details in the sidebar to continue")
    st.stop()

tab1, tab2, tab3 = st.tabs(["🗺️ Plan Itinerary", "🎫 Book Trip", "📊 My Bookings"])

with tab1:
    st.header("Create Your Travel Itinerary")

    col1, col2 = st.columns([2, 1])

    with col1:
        with st.form("itinerary_form"):
            city = st.text_input(
                "Destination City",
                placeholder="e.g., Paris, Tokyo, New York",
                help="Enter the city you want to visit"
            )
            interests = st.text_input(
                "Your Interests",
                placeholder="e.g., museums, food, nightlife, beaches",
                help="Comma-separated list of your interests"
            )

            generate_btn = st.form_submit_button("Generate Itinerary", type="primary", use_container_width=True)

            if generate_btn:
                if city and interests:
                    with st.spinner("Creating your personalized itinerary..."):
                        result, error = create_itinerary(
                            city=city,
                            interests=interests,
                            user_email=st.session_state.user_email,
                            user_name=st.session_state.user_name
                        )

                        if result:
                            st.session_state.current_itinerary = result
                            st.session_state.user_id = result.get('user_id')
                            st.success("Itinerary created successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to create itinerary: {error}")
                else:
                    st.warning("Please enter both city and interests")

    with col2:
        st.subheader("Popular Destinations")
        st.markdown("""
        - Paris, France
        - Tokyo, Japan
        - New York, USA
        - Barcelona, Spain
        - Dubai, UAE
        - Singapore
        - London, UK
        - Rome, Italy
        """)

    if st.session_state.current_itinerary:
        st.divider()
        st.subheader(f"Your Itinerary for {st.session_state.current_itinerary.get('city')}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Destination", st.session_state.current_itinerary.get('city'))
        with col2:
            st.metric("Status", st.session_state.current_itinerary.get('status', 'draft').upper())
        with col3:
            st.metric("Itinerary ID", st.session_state.current_itinerary.get('itinerary_id')[:8] + "...")

        st.markdown("---")
        st.markdown(st.session_state.current_itinerary.get('content', 'No content available'))

        st.info("Ready to book? Go to the 'Book Trip' tab to complete your reservation.")

with tab2:
    st.header("Book Your Trip")

    if not st.session_state.current_itinerary:
        st.warning("Please create an itinerary first in the 'Plan Itinerary' tab")
    else:
        itinerary = st.session_state.current_itinerary

        st.subheader(f"Booking Details: {itinerary.get('city')}")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("**Itinerary Preview:**")
            preview = itinerary.get('content', '')[:300] + "..." if len(itinerary.get('content', '')) > 300 else itinerary.get('content', '')
            st.text_area("", preview, height=150, disabled=True)

        with col2:
            st.markdown("**Pricing:**")
            st.metric("Trip Cost", "$299.99")
            st.caption("Includes guided tours and entrance fees")

        st.divider()

        with st.form("booking_form"):
            st.subheader("Payment Information")

            payment_method = st.selectbox(
                "Payment Method",
                ["credit_card", "debit_card", "paypal", "new_card"],
                format_func=lambda x: {
                    "credit_card": "Credit Card",
                    "debit_card": "Debit Card",
                    "paypal": "PayPal",
                    "new_card": "New Card"
                }.get(x, x)
            )

            st.caption("Note: New cards may require additional fraud verification")

            col1, col2 = st.columns(2)
            with col1:
                agree = st.checkbox("I agree to the terms and conditions")
            with col2:
                book_btn = st.form_submit_button("Complete Booking", type="primary", use_container_width=True)

            if book_btn:
                if not agree:
                    st.error("Please agree to the terms and conditions")
                else:
                    with st.spinner("Processing your booking and payment..."):
                        booking_result, error = create_booking(
                            itinerary_id=itinerary.get('itinerary_id'),
                            user_id=st.session_state.user_id,
                            payment_method=payment_method
                        )

                        if booking_result:
                            st.session_state.booking_history.append(booking_result)

                            if booking_result.get('status') == 'confirmed':
                                st.success("Booking confirmed successfully!")

                                fraud_check = booking_result.get('fraud_check', {})

                                st.balloons()

                                st.subheader("Booking Confirmation")

                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Booking ID", booking_result.get('booking_id', 'N/A')[:8] + "...")
                                with col2:
                                    st.metric("Payment ID", booking_result.get('payment_id', 'N/A')[:8] + "...")
                                with col3:
                                    st.metric("Status", booking_result.get('status', 'Unknown').upper())

                                st.divider()

                                st.subheader("Security Check Results")
                                col1, col2 = st.columns(2)
                                with col1:
                                    risk_score = fraud_check.get('risk_score', 0)
                                    st.metric("Risk Score", f"{risk_score}/100")

                                    if risk_score < 30:
                                        st.success("Low risk transaction")
                                    elif risk_score < 60:
                                        st.warning("Medium risk transaction")
                                    else:
                                        st.error("High risk transaction")

                                with col2:
                                    st.metric("Security Status", fraud_check.get('status', 'Unknown').upper())
                                    st.caption(fraud_check.get('reason', 'No additional information'))

                                st.info("A confirmation email will be sent to your registered email address")

                                st.session_state.current_itinerary = None
                            else:
                                st.error("Booking failed - Payment was not approved")

                                fraud_check = booking_result.get('fraud_check', {})
                                st.warning(f"Reason: {fraud_check.get('reason', 'Unknown')}")
                                st.metric("Risk Score", f"{fraud_check.get('risk_score', 0)}/100")
                        else:
                            st.error(f"Booking failed: {error}")

with tab3:
    st.header("My Booking History")

    if not st.session_state.booking_history:
        st.info("No bookings yet. Create an itinerary and book your first trip!")
    else:
        st.subheader(f"Total Bookings: {len(st.session_state.booking_history)}")

        for idx, booking in enumerate(reversed(st.session_state.booking_history)):
            with st.expander(f"Booking #{len(st.session_state.booking_history) - idx} - {booking.get('booking_id', 'Unknown')[:16]}..."):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Booking ID", booking.get('booking_id', 'N/A')[:12] + "...")
                with col2:
                    st.metric("Payment ID", booking.get('payment_id', 'N/A')[:12] + "...")
                with col3:
                    status = booking.get('status', 'Unknown')
                    if status == 'confirmed':
                        st.success(f"Status: {status.upper()}")
                    else:
                        st.error(f"Status: {status.upper()}")
                with col4:
                    fraud_check = booking.get('fraud_check', {})
                    st.metric("Risk Score", f"{fraud_check.get('risk_score', 0)}/100")

                st.divider()

                st.markdown("**Security Details:**")
                st.caption(f"Status: {fraud_check.get('status', 'Unknown')}")
                st.caption(f"Reason: {fraud_check.get('reason', 'No information')}")

                if st.button(f"View Full Details", key=f"view_{idx}"):
                    with st.spinner("Loading booking details..."):
                        details, error = get_booking_details(booking.get('booking_id'))
                        if details:
                            st.json(details)
                        else:
                            st.error(f"Failed to load details: {error}")

st.divider()
st.caption("Powered by Enterprise Microservices Architecture | Secure Payment Processing | Real-time Fraud Detection")
st.caption(f"Gateway URL: {GATEWAY_URL}")
