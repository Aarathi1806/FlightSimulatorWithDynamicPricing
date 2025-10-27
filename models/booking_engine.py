import random
import string
from datetime import datetime, timedelta
from database.db_config import get_connection

def generate_pnr():
    """Generate a unique 6-character PNR code (4 letters + 2 numbers)"""
    letters = string.ascii_uppercase
    numbers = string.digits

    pnr = ''.join(random.choice(letters) for _ in range(4)) + ''.join(random.choice(numbers) for _ in range(2))
    return pnr

def check_seat_availability(flight_type, flight_id, seat_no):
    """Check if a specific seat is available for booking"""
    try:
        conn = get_connection()
        if not conn:
            return False, "Database connection failed"
        
        cursor = conn.cursor(dictionary=True)
        
        if flight_type.upper() == 'DOMESTIC':
            # Check if seat is already booked
            cursor.execute("""
                SELECT COUNT(*) as count FROM bookings 
                WHERE flight_type = 'DOMESTIC' AND flight_ref_id = %s AND seat_no = %s AND status != 'CANCELLED'
            """, (flight_id, seat_no))
            result = cursor.fetchone()
            
            # Check if flight exists and has available seats
            cursor.execute("""
                SELECT seats_available FROM domestic_flights WHERE flight_id = %s
            """, (flight_id,))
            flight_info = cursor.fetchone()
            
        else:  # INTERNATIONAL
            cursor.execute("""
                SELECT COUNT(*) as count FROM bookings 
                WHERE flight_type = 'INTERNATIONAL' AND flight_ref_id = %s AND seat_no = %s AND status != 'CANCELLED'
            """, (flight_id, seat_no))
            result = cursor.fetchone()
            
            cursor.execute("""
                SELECT seats_available FROM international_flights WHERE intl_id = %s
            """, (flight_id,))
            flight_info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result['count'] > 0:
            return False, "Seat already booked"
        
        if not flight_info:
            return False, "Flight not found"
        
        if flight_info['seats_available'] <= 0:
            return False, "No seats available"
        
        return True, "Seat available"
        
    except Exception as e:
        return False, f"Error checking seat availability: {str(e)}"

def calculate_fare(flight_type, flight_id, apply_dynamic_pricing=True):
    """Calculate the final fare for a booking"""
    try:
        from models.pricing_engine import calculate_dynamic_price
        
        conn = get_connection()
        if not conn:
            return None, "Database connection failed"
        
        cursor = conn.cursor(dictionary=True)
        
        if flight_type.upper() == 'DOMESTIC':
            cursor.execute("""
                SELECT f.*, at.tier_factor 
                FROM domestic_flights f
                JOIN airline_tiers at ON f.airline_id = at.airline_id
                WHERE f.flight_id = %s
            """, (flight_id,))
        else:
            cursor.execute("""
                SELECT f.*, at.tier_factor 
                FROM international_flights f
                JOIN airline_tiers at ON f.airline_id = at.airline_id
                WHERE f.intl_id = %s
            """, (flight_id,))
        
        flight = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not flight:
            return None, "Flight not found"
        
        base_fare = float(flight['base_fare'])
        
        if apply_dynamic_pricing:
            result = calculate_dynamic_price(
                base_fare=base_fare,
                total_seats=flight['total_seats'],
                seats_available=flight['seats_available'],
                departure_time=flight['departure'],
                tier_factor=float(flight['tier_factor'])
            )
            return result['new_price'], "Fare calculated"
        
        return base_fare, "Fare calculated"
        
    except Exception as e:
        return None, f"Error calculating fare: {str(e)}"

def simulate_payment(amount, payment_mode):
    """Simulate payment processing with success/failure scenarios"""
    # 90% success rate for demonstration
    if random.random() > 0.1:
        return {
            "status": "SUCCESS",
            "transaction_id": "TXN" + ''.join([random.choice(string.digits) for _ in range(12)]),
            "payment_time": datetime.now().isoformat()
        }
    else:
        return {
            "status": "FAILED",
            "error": "Payment gateway timeout",
            "payment_time": datetime.now().isoformat()
        }

def validate_booking_data(data):
    """Validate booking request data"""
    required_fields = ['flight_type', 'flight_id', 'seat_no', 'passenger_info', 'payment_info']
    
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    if data['flight_type'] not in ['DOMESTIC', 'INTERNATIONAL']:
        return False, "Invalid flight_type. Must be DOMESTIC or INTERNATIONAL"
    
    if 'email' not in data['passenger_info'] or 'full_name' not in data['passenger_info']:
        return False, "Missing required passenger information"
    
    if 'payment_mode' not in data['payment_info']:
        return False, "Missing payment mode"
    
    return True, "Valid"
