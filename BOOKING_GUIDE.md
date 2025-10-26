# Booking Workflow Implementation Guide
The booking workflow implements a complete end-to-end booking process with:
- **Concurrency Control**: Using database transactions and row-level locking
- **PNR Generation**: Unique 6-character PNR codes
- **Payment Simulation**: Success/fail scenarios
- **Seat Availability**: Real-time seat validation
- **Dynamic Pricing**: Integrated with pricing engine
- **Cancellation**: Full refund and seat release

## 🚀 API Endpoints

### 1. Create Booking
**POST** `/bookings/create`

Create a new booking with concurrency control.

**Request Body:**
```json
{
  "flight_type": "DOMESTIC",
  "flight_id": 1,
  "seat_no": "A12",
  "passenger_info": {
    "full_name": "John Doe",
    "email": "john@example.com",
    "contact_no": "9876543210",
    "nationality": "Indian",
    "passport_no": "P1234567",
    "visa_status": "N/A"
  },
  "payment_info": {
    "payment_mode": "Credit Card"
  }
}
```

**Response (201):**
```json
{
  "status": "success",
  "message": "Booking confirmed",
  "booking_id": 5,
  "pnr": "A1B2C3",
  "booking_details": {...},
  "payment_status": "SUCCESS",
  "transaction_id": "TXN123456789012"
}
```

---

### 2. Get Booking by ID
**GET** `/bookings/<booking_id>`

Retrieve booking details by booking ID.

**Response (200):**
```json
{
  "booking": {
    "booking_id": 5,
    "pnr_code": "A1B2C3",
    "passenger_name": "John Doe",
    "status": "CONFIRMED",
  }
}
```

---

### 3. Get Booking by PNR
**GET** `/bookings/pnr/<pnr_code>`

Retrieve booking details by PNR code.

**Example:** `GET /bookings/pnr/A1B2C3`

---

### 4. Cancel Booking
**POST** `/bookings/<booking_id>/cancel`

Cancel a booking and process refund.

**Response (200):**
```json
{
  "status": "success",
  "message": "Booking cancelled successfully",
  "booking_id": 5,
  "refund_status": "Processed"
}
```

---

### 5. Get Passenger Bookings
**GET** `/bookings/passenger/<passenger_id>`

Get all bookings for a specific passenger.

**Response (200):**
```json
{
  "bookings": [...],
  "total": 3
}
```

---

### 6. Check Seat Availability
**GET** `/bookings/check-seat`

Check if a specific seat is available.

**Query Parameters:**
- `flight_type`: DOMESTIC or INTERNATIONAL
- `flight_id`: Flight ID
- `seat_no`: Seat number (e.g., "A12")

**Example:** `GET /bookings/check-seat?flight_type=DOMESTIC&flight_id=1&seat_no=A12`

**Response (200):**
```json
{
  "available": true,
  "message": "Seat available",
  "flight_type": "DOMESTIC",
  "flight_id": 1,
  "seat_no": "A12"
}
```

---

### 7. Calculate Booking Fare
**POST** `/bookings/calculate-fare`

Calculate fare for a booking (with or without dynamic pricing).

**Request Body:**
```json
{
  "flight_type": "DOMESTIC",
  "flight_id": 1,
  "apply_dynamic_pricing": true
}
```

**Response (200):**
```json
{
  "fare": 7500.50,
  "message": "Fare calculated",
  "flight_type": "DOMESTIC",
  "flight_id": 1,
  "dynamic_pricing_applied": true
}
```

---

## 🔒 Concurrency Control Features

### 1. **Database Transactions**
- All booking operations use `START TRANSACTION` and `COMMIT/ROLLBACK`
- Ensures atomicity and consistency

### 2. **Row-Level Locking**
- Uses `FOR UPDATE` clause to lock seats during booking
- Prevents double-booking in concurrent scenarios

### 3. **Seat Validation**
- Checks seat availability before and during transaction
- Returns 409 Conflict if seat no longer available

### 4. **Unique PNR Generation**
- Generates unique 6-character PNR codes
- Checks for duplicates and regenerates if needed

---

## 💳 Payment Simulation

The payment system includes:
- **90% Success Rate**: Random success/failure for testing
- **Transaction IDs**: Unique transaction IDs for successful payments
- **Payment Modes**: Credit Card, Debit Card, UPI, Net Banking
- **Refund Processing**: Automatic refund on cancellation

---

## 📊 Booking Flow Diagram

```
1. Validate Request Data
   ↓
2. Check Seat Availability (Initial Check)
   ↓
3. Calculate Fare (with Dynamic Pricing)
   ↓
4. Start Database Transaction
   ↓
5. Lock Seat with FOR UPDATE
   ↓
6. Validate Seat Again (Concurrency Control)
   ↓
7. Check/Create Passenger
   ↓
8. Process Payment
   ↓
9. Generate Unique PNR
   ↓
10. Create Booking Record
   ↓
11. Create Payment Record
   ↓
12. Update Seat Availability
   ↓
13. Commit Transaction
   ↓
14. Return Booking Confirmation
```

---

## 🧪 Testing Examples

### Test Case 1: Successful Booking

```bash
curl -X POST http://localhost:5000/bookings/create \
  -H "Content-Type: application/json" \
  -d '{
    "flight_type": "DOMESTIC",
    "flight_id": 1,
    "seat_no": "A15",
    "passenger_info": {
      "full_name": "Jane Smith",
      "email": "jane@example.com",
      "contact_no": "9876543211",
      "nationality": "Indian"
    },
    "payment_info": {
      "payment_mode": "Credit Card"
    }
  }'
```

### Test Case 2: Check Seat

```bash
curl "http://localhost:5000/bookings/check-seat?flight_type=DOMESTIC&flight_id=1&seat_no=A15"
```

### Test Case 3: Calculate Fare

```bash
curl -X POST http://localhost:5000/bookings/calculate-fare \
  -H "Content-Type: application/json" \
  -d '{
    "flight_type": "DOMESTIC",
    "flight_id": 1,
    "apply_dynamic_pricing": true
  }'
```

### Test Case 4: Retrieve Booking by PNR

```bash
curl "http://localhost:5000/bookings/pnr/A1B2C3"
```

### Test Case 5: Cancel Booking

```bash
curl -X POST http://localhost:5000/bookings/5/cancel
```
---

## ✨ Key Features Implemented

✅ **Multi-step booking flow**
- Flight & seat selection
- Passenger information collection
- Payment processing
- PNR generation

✅ **Concurrency-safe seat reservations**
- Database transactions
- Row-level locking
- Double-booking prevention

✅ **Unique PNR assignment**
- 6-character alphanumeric codes
- Uniqueness validation
- Indexed for fast lookups

✅ **Booking storage**
- Complete booking history
- Payment records
- Passenger information

✅ **Functional cancellation**
- Booking status update
- Seat release
- Refund processing
- Transaction safety

✅ **History retrieval**
- By booking ID
- By PNR code
- By passenger ID

---

## 📝 Notes

- The PNR codes are auto-generated and unique
- Dynamic pricing is integrated into the booking process
- Payment simulation uses a 90% success rate for testing
- All transactions are ACID compliant
- Seat availability is updated in real-time
