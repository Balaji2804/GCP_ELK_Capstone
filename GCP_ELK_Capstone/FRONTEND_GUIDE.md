# Enterprise Frontend Guide - Streamlit UI

## Overview

The Streamlit frontend has been completely redesigned to integrate with the microservices backend architecture. It now provides a full booking flow with payment processing, fraud detection, and booking history tracking.

---

## Key Features

### 1. User Authentication Flow
- User registration with email and name
- Session management using Streamlit state
- Logout functionality
- User profile sidebar

### 2. Three-Tab Interface

#### Tab 1: Plan Itinerary
- AI-powered itinerary generation
- City and interests input
- Itinerary preview
- Popular destinations suggestions
- Session state management for current itinerary

#### Tab 2: Book Trip
- Complete booking flow
- Payment method selection (Credit Card, Debit Card, PayPal, New Card)
- Terms and conditions agreement
- Real-time payment processing
- Fraud detection results display
- Risk score visualization
- Booking confirmation with balloons animation

#### Tab 3: My Bookings
- Booking history view
- Expandable booking cards
- Booking details (ID, Payment ID, Status, Risk Score)
- Full booking details retrieval
- Security information display

---

## Architecture Changes

### Before (Monolith):
```python
# Direct LLM calls
planner = TravelPlanner()
planner.set_city(city)
planner.set_interests(interests)
itinerary = planner.create_itinerary()
```

### After (Microservices):
```python
# API calls to Gateway Service
response = client.post(
    f"{GATEWAY_URL}/api/itineraries",
    json={
        "city": city,
        "interests": interests,
        "user_email": user_email,
        "user_name": user_name
    }
)
```

---

## API Integration

### 1. Create Itinerary
**Endpoint**: `POST /api/itineraries`

**Request**:
```json
{
  "city": "Paris",
  "interests": "museums, food, wine",
  "user_email": "user@example.com",
  "user_name": "John Doe"
}
```

**Response**:
```json
{
  "itinerary_id": "uuid",
  "user_id": "uuid",
  "city": "Paris",
  "content": "AI-generated itinerary...",
  "status": "draft"
}
```

### 2. Create Booking
**Endpoint**: `POST /api/bookings`

**Request**:
```json
{
  "itinerary_id": "uuid",
  "user_id": "uuid",
  "payment_method": "credit_card"
}
```

**Response**:
```json
{
  "booking_id": "uuid",
  "payment_id": "uuid",
  "status": "confirmed",
  "fraud_check": {
    "fraud_check_id": "uuid",
    "risk_score": 25.5,
    "status": "approved",
    "reason": "No risk factors detected"
  }
}
```

### 3. Get Booking Details
**Endpoint**: `GET /api/bookings/{booking_id}`

**Response**:
```json
{
  "id": "uuid",
  "itinerary_id": "uuid",
  "user_id": "uuid",
  "status": "confirmed",
  "total_amount": "299.99",
  "payment_id": "uuid",
  "itineraries": {...},
  "payments": {...}
}
```

---

## Environment Variables

### Required:
- `GATEWAY_URL` - URL of the Gateway Service (default: `http://gateway-service:8000`)

### Kubernetes Deployment:
```yaml
env:
  - name: GATEWAY_URL
    value: "http://gateway-service:8000"
```

### Local Development:
```bash
export GATEWAY_URL="http://localhost:8000"
```

---

## Session State Management

The frontend uses Streamlit session state to maintain:

```python
st.session_state.user_id = None           # Current user UUID
st.session_state.user_email = None        # User email
st.session_state.user_name = None         # User full name
st.session_state.current_itinerary = None # Active itinerary object
st.session_state.booking_history = []     # List of completed bookings
```

---

## User Flow Diagram

```
1. User Login
   └─> Enter email and name
   └─> Session state updated

2. Create Itinerary (Tab 1)
   └─> Enter city and interests
   └─> Click "Generate Itinerary"
   └─> API call to /api/itineraries
   └─> Itinerary displayed
   └─> Stored in session_state.current_itinerary

3. Book Trip (Tab 2)
   └─> View itinerary preview
   └─> Select payment method
   └─> Agree to terms
   └─> Click "Complete Booking"
   └─> API call to /api/bookings
   │   └─> Booking Service creates booking
   │   └─> Payment Service processes payment
   │   └─> Fraud Service checks transaction
   │   └─> Notification Service sends email (async)
   └─> Display booking confirmation
   └─> Show fraud check results
   └─> Add to booking_history

4. View Bookings (Tab 3)
   └─> Display all bookings from session
   └─> Expand booking to view details
   └─> Click "View Full Details" for complete data
   └─> API call to /api/bookings/{id}
```

---

## UI Components

### Sidebar
- User profile card
- Login/Logout buttons
- Quick stats (Total Bookings, Active Itinerary)

### Main Area
- Tabs navigation
- Forms with validation
- Metrics cards
- Status indicators
- Progress spinners
- Success/Error messages
- Balloons animation on successful booking

### Color Coding
- **Green**: Successful bookings, low risk scores
- **Yellow**: Medium risk scores
- **Red**: Failed bookings, high risk scores
- **Blue**: Info messages, active itineraries

---

## Error Handling

The frontend includes comprehensive error handling:

```python
try:
    response = client.post(...)
    if response.status_code == 200:
        return response.json(), None
    else:
        return None, f"Error {response.status_code}: {response.text}"
except Exception as e:
    return None, f"Connection error: {str(e)}"
```

Error messages are displayed using:
- `st.error()` for critical errors
- `st.warning()` for warnings
- `st.info()` for informational messages

---

## Deployment

### 1. Update requirements.txt
```bash
# Already updated with httpx
cat requirements.txt
```

### 2. Rebuild Docker Image
```bash
docker build -t streamlit-app:latest .
docker tag streamlit-app:latest <AWS_ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/streamlit-app:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/streamlit-app:latest
```

### 3. Deploy to Kubernetes
```bash
kubectl apply -f k8s-deployment.yaml
kubectl rollout restart deployment streamlit-app
```

### 4. Verify Deployment
```bash
kubectl get pods -l app=streamlit
kubectl logs -l app=streamlit --tail=50
```

### 5. Access the App
```bash
kubectl get svc streamlit-service
# Access via LoadBalancer URL
```

---

## Testing the Frontend

### Manual Testing Checklist

1. **User Login**
   - [ ] Enter email and name
   - [ ] Verify session state is set
   - [ ] Check sidebar shows user info
   - [ ] Test logout functionality

2. **Create Itinerary**
   - [ ] Enter city: "Paris"
   - [ ] Enter interests: "museums, food, wine"
   - [ ] Click "Generate Itinerary"
   - [ ] Verify AI-generated content appears
   - [ ] Check itinerary ID is displayed
   - [ ] Verify status shows "DRAFT"

3. **Book Trip**
   - [ ] Navigate to "Book Trip" tab
   - [ ] Verify itinerary preview is shown
   - [ ] Select payment method
   - [ ] Check "I agree to terms"
   - [ ] Click "Complete Booking"
   - [ ] Verify booking confirmation appears
   - [ ] Check fraud detection results
   - [ ] Verify balloons animation plays (if approved)

4. **View Bookings**
   - [ ] Navigate to "My Bookings" tab
   - [ ] Verify booking appears in history
   - [ ] Expand booking card
   - [ ] Click "View Full Details"
   - [ ] Verify complete booking data is shown

5. **Error Handling**
   - [ ] Try booking without itinerary
   - [ ] Try booking without agreeing to terms
   - [ ] Test with invalid payment method
   - [ ] Verify error messages are displayed

---

## Differences from Original Frontend

| Aspect | Before (Monolith) | After (Microservices) |
|--------|-------------------|----------------------|
| **UI Layout** | Single form | Three-tab interface |
| **User Management** | None | Email/Name with session |
| **Itinerary Creation** | Direct LLM call | API call to Gateway |
| **Booking Flow** | Not available | Complete booking + payment |
| **Fraud Detection** | Not available | Real-time fraud check display |
| **Payment Processing** | Not available | Multiple payment methods |
| **Booking History** | Not available | Persistent session history |
| **Error Handling** | Basic warnings | Comprehensive error display |
| **API Integration** | None | Full REST API integration |
| **State Management** | None | Session state for user data |

---

## Screenshots Description

### Login Screen
- Sidebar form with email and name inputs
- "Continue" button
- Clean, minimal design

### Plan Itinerary Tab
- Two-column layout
- Left: City and interests form
- Right: Popular destinations list
- Bottom: Generated itinerary display
- Metrics cards showing destination, status, ID

### Book Trip Tab
- Itinerary preview (300 chars)
- Pricing information ($299.99)
- Payment method dropdown
- Terms and conditions checkbox
- "Complete Booking" button
- Success: Booking confirmation with metrics
- Success: Fraud check results with risk score
- Failure: Error message with reason

### My Bookings Tab
- List of expandable booking cards
- Each card shows: Booking ID, Payment ID, Status, Risk Score
- "View Full Details" button
- JSON display of complete booking data

---

## Performance Considerations

1. **HTTP Timeouts**:
   - Itinerary creation: 60 seconds
   - Booking creation: 90 seconds
   - Booking details: 30 seconds

2. **Session State**:
   - Lightweight data storage
   - Cleared on logout
   - No persistence across browser sessions

3. **API Calls**:
   - Synchronous HTTP calls using httpx
   - Error handling for timeouts
   - User feedback via spinners

---

## Future Enhancements

1. **Authentication**:
   - Real user authentication (Supabase Auth)
   - Password-based login
   - OAuth providers

2. **Persistence**:
   - Store booking history in database
   - Retrieve user's past bookings on login

3. **Real-time Updates**:
   - WebSocket for payment status updates
   - Live fraud detection progress

4. **Enhanced UI**:
   - Custom CSS styling
   - Animation improvements
   - Mobile responsiveness

5. **Features**:
   - Booking cancellation
   - Booking modification
   - Multiple itineraries per user
   - Share itinerary via link
   - Export itinerary as PDF

---

## Troubleshooting

### Issue: "Connection error: Connection refused"
**Cause**: Gateway service not running or wrong URL

**Solution**:
```bash
# Verify gateway service is running
kubectl get svc gateway-service

# Check GATEWAY_URL environment variable
kubectl exec -it <streamlit-pod> -- env | grep GATEWAY_URL

# Restart streamlit pod
kubectl rollout restart deployment streamlit-app
```

### Issue: "Failed to create itinerary: Error 500"
**Cause**: Backend service error (likely Booking Service)

**Solution**:
```bash
# Check booking service logs
kubectl logs -l app=booking-service --tail=100

# Verify GROQ_API_KEY is set
kubectl get secret microservices-secrets -o json | jq -r '.data.GROQ_API_KEY' | base64 -d
```

### Issue: "Payment rejected: Fraud detected"
**Cause**: Fraud service flagged the transaction

**Solution**: This is expected behavior for high-risk transactions. Try:
- Different payment method (not "new_card")
- Wait a few seconds and retry
- Check fraud service logs for details

### Issue: Booking history lost after refresh
**Cause**: Session state is not persisted

**Solution**: This is by design. To persist:
- Store bookings in database
- Retrieve on user login
- Implement real authentication

---

## Summary

The frontend has been completely transformed from a simple itinerary generator to an enterprise-grade booking platform that:

- Integrates with microservices backend
- Provides complete booking flow
- Shows payment processing results
- Displays fraud detection analysis
- Maintains booking history
- Handles errors gracefully
- Provides professional UX

All API calls now go through the Gateway Service, which routes to appropriate microservices. The frontend is stateless (except session state) and can be scaled independently.
