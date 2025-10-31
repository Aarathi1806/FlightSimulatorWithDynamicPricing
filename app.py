from datetime import datetime
from flask import Flask, jsonify, render_template, session, redirect, request
from flask_cors import CORS
from database.db_config import get_connection
from models.pricing_engine import calculate_dynamic_price
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.secret_key = 'flight-simulator-secret-key-2025'
CORS(app)

# ============================================
# LOGIN REQUIRED DECORATOR
# ============================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/ui/login')
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# ROOT ROUTE - ENTRY POINT
# ============================================
@app.route("/")
def root():
    """Entry point - redirect to login or home based on session"""
    if 'user_id' in session:
        return redirect('/ui')
    return redirect('/ui/login')

# ============================================
# AUTHENTICATION ROUTES (NO LOGIN REQUIRED)
# ============================================
@app.route("/ui/login")
def ui_login():
    """Login page"""
    if 'user_id' in session:
        return redirect('/ui')
    return render_template('login.html', title='Login')

@app.route("/ui/signup")
def ui_signup():
    """Signup page"""
    if 'user_id' in session:
        return redirect('/ui')
    return render_template('signup.html', title='Sign Up')

@app.route("/auth/signup", methods=['POST'])
def auth_signup():
    """Handle user signup"""
    try:
        data = request.get_json()
        
        required_fields = ['email', 'phone_number', 'password', 'full_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        email = data['email'].strip().lower()
        phone_number = data['phone_number'].strip()
        password = data['password']
        full_name = data['full_name'].strip()
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        
        password_hash = generate_password_hash(password)
        
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Check email
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Email already registered"}), 400
        
        # Check phone
        cursor.execute("SELECT user_id FROM users WHERE phone_number = %s", (phone_number,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Phone number already registered"}), 400
        
        # Create user
        cursor.execute("""
            INSERT INTO users (email, phone_number, password_hash, full_name)
            VALUES (%s, %s, %s, %s)
        """, (email, phone_number, password_hash, full_name))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Account created successfully",
            "user_id": user_id
        }), 201
        
    except Exception as e:
        print(f"❌ Error in signup: {e}")
        return jsonify({"error": f"Signup failed: {str(e)}"}), 500

@app.route("/auth/login", methods=['POST'])
def auth_login():
    """Handle user login"""
    try:
        data = request.get_json()
        
        identifier = data.get('identifier', '').strip()
        password = data.get('password', '')
        
        if not identifier or not password:
            return jsonify({"error": "Email/phone and password are required"}), 400
        
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        if '@' in identifier:
            cursor.execute("SELECT * FROM users WHERE email = %s", (identifier.lower(),))
        else:
            cursor.execute("SELECT * FROM users WHERE phone_number = %s", (identifier,))
        
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid email/phone or password"}), 401
        
        if not check_password_hash(user['password_hash'], password):
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid email/phone or password"}), 401
        
        cursor.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user['user_id'],))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        session['user_id'] = user['user_id']
        session['email'] = user['email']
        session['full_name'] = user['full_name']
        
        return jsonify({
            "status": "success",
            "message": "Login successful",
            "user": {
                "user_id": user['user_id'],
                "email": user['email'],
                "full_name": user['full_name'],
                "phone_number": user['phone_number']
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error in login: {e}")
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@app.route("/auth/logout", methods=['POST', 'GET'])
def auth_logout():
    """Handle user logout"""
    session.clear()
    if request.method == 'GET':
        return redirect('/ui/login')
    return jsonify({"status": "success", "message": "Logged out successfully"}), 200

@app.route("/auth/check-session", methods=['GET'])
def check_session():
    """Check if user is logged in"""
    if 'user_id' in session:
        return jsonify({
            "logged_in": True,
            "user": {
                "user_id": session['user_id'],
                "email": session['email'],
                "full_name": session['full_name']
            }
        }), 200
    else:
        return jsonify({"logged_in": False}), 200

# ============================================
# PROTECTED UI ROUTES (LOGIN REQUIRED)
# ============================================
@app.route("/ui")
@login_required
def ui_home():
    """Home page - protected"""
    return render_template('home.html', title='FlightSim - Home')

@app.route("/ui/search")
@login_required
def ui_search():
    """Search flights page - protected"""
    return render_template('search.html', title='Search Flights')

@app.route("/ui/flights")
@login_required
def ui_flights():
    """Browse flights page - protected"""
    return render_template('flights.html', title='Browse Flights')

@app.route("/ui/booking/<flight_type>/<int:flight_id>")
@login_required
def ui_booking(flight_type, flight_id):
    """Booking page - protected"""
    conn = get_connection()
    if not conn:
        return render_template('booking.html', title='Booking', flight_type=flight_type, flight_id=flight_id, flight={"flight_no":"N/A","origin":"","destination":"","departure":"","total_seats":0,"seats_available":0}, booked_seats=[])
    
    cursor = conn.cursor(dictionary=True)
    if flight_type.upper() == 'DOMESTIC':
        cursor.execute("SELECT * FROM domestic_flights WHERE flight_id=%s", (flight_id,))
    else:
        cursor.execute("SELECT * FROM international_flights WHERE intl_id=%s", (flight_id,))
    
    flight = cursor.fetchone() or {}
    
    cursor.execute(
        """
        SELECT seat_no FROM bookings
        WHERE flight_type=%s AND flight_ref_id=%s AND status != 'CANCELLED'
        """,
        (flight_type.upper(), flight_id),
    )
    booked_rows = cursor.fetchall() or []
    booked_seats = [r.get('seat_no') for r in booked_rows if r.get('seat_no')]
    cursor.close(); conn.close()
    
    if flight_type.upper() == 'INTERNATIONAL' and flight:
        flight['flight_id'] = flight.get('intl_id')
    
    return render_template('booking.html', title='Booking', flight_type=flight_type.upper(), flight_id=flight_id, flight=flight, booked_seats=booked_seats)

@app.route("/ui/my-bookings")
@login_required
def ui_my_bookings():
    """My bookings page - protected"""
    return render_template('my_bookings.html', title='My Bookings')

# ============================================
# API ROUTES - FLIGHTS
# ============================================
@app.route("/test")
def test_db():
    """Test database connection"""
    try:
        conn = get_connection()
        if conn:
            conn.close()
            return jsonify({"status": "Database connected successfully ✅"})
        return jsonify({"status": "Database connection failed ❌"})
    except Exception as e:
        return jsonify({"status": f"Database connection failed - Error: {str(e)}"})

@app.route("/flights/domestic")
def domestic_flights():
    """Get all domestic flights"""
    try:
        print("Fetching domestic flights...")
        from models.queries import get_domestic_flights
        flights = get_domestic_flights()
        print(f"Retrieved {len(flights)} flights")
        if not flights:
            return jsonify({"message": "No domestic flights found", "domestic_flights": []})
        return jsonify({"domestic_flights": flights})
    except Exception as e:
        print(f"Error in domestic_flights endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/flights/international")
def international_flights():
    """Get all international flights"""
    try:
        print("Fetching international flights...")
        from models.queries import get_international_flights
        flights = get_international_flights()
        print(f"Retrieved {len(flights)} flights")
        if not flights:
            return jsonify({"message": "No international flights found", "international_flights": []})
        return jsonify({"international_flights": flights})
    except Exception as e:
        print(f"Error in international_flights endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/flights/all")
def all_flights():
    """Get all flights with dynamic pricing"""
    try:
        print("📡 Fetching all flights with dynamic prices...")
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT f.*, a.airline_name, at.tier_factor
            FROM domestic_flights f
            JOIN airlines a ON f.airline_id = a.airline_id
            JOIN airline_tiers at ON f.airline_id = at.airline_id
            ORDER BY f.departure ASC
        """)
        domestic_rows = cursor.fetchall() or []
        
        cursor.execute("""
            SELECT f.*, a.airline_name, at.tier_factor
            FROM international_flights f
            JOIN airlines a ON f.airline_id = a.airline_id
            JOIN airline_tiers at ON f.airline_id = at.airline_id
            ORDER BY f.departure ASC
        """)
        intl_rows = cursor.fetchall() or []
        
        domestic = []
        for f in domestic_rows:
            pricing = calculate_dynamic_price(
                base_fare=float(f['base_fare']),
                total_seats=int(f['total_seats']),
                seats_available=int(f['seats_available']),
                departure_time=f['departure'],
                tier_factor=float(f['tier_factor'])
            )
            item = dict(f)
            item['dynamic_price'] = pricing['new_price']
            domestic.append(item)
        
        international = []
        for f in intl_rows:
            pricing = calculate_dynamic_price(
                base_fare=float(f['base_fare']),
                total_seats=int(f['total_seats']),
                seats_available=int(f['seats_available']),
                departure_time=f['departure'],
                tier_factor=float(f['tier_factor'])
            )
            item = dict(f)
            item['dynamic_price'] = pricing['new_price']
            international.append(item)
        
        cursor.close(); conn.close()
        
        return jsonify({
            "domestic_flights": domestic,
            "international_flights": international,
            "total_domestic": len(domestic),
            "total_international": len(international)
        })
    except Exception as e:
        print(f"❌ Error in all_flights endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/flights/search")
def search_flights():
    """Search flights by origin, destination, date"""
    try:
        origin = request.args.get('origin', '').strip().title()
        destination = request.args.get('destination', '').strip().title()
        departure_date = request.args.get('date', '').strip()
        sort_by = request.args.get('sort', 'price')
        sort_order = request.args.get('order', 'asc')
        include_pricing = request.args.get('pricing', 'false').lower() == 'true'
        
        print(f"🔍 Searching flights: {origin} → {destination} on {departure_date}")
        
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        domestic_query = """
            SELECT f.*, a.airline_name, at.tier_factor,
            TIMESTAMPDIFF(MINUTE, f.departure, f.arrival) as duration_minutes
            FROM domestic_flights f
            JOIN airlines a ON f.airline_id = a.airline_id
            JOIN airline_tiers at ON f.airline_id = at.airline_id
            WHERE 1=1
        """
        domestic_params = []
        
        if origin:
            domestic_query += " AND f.origin LIKE %s"
            domestic_params.append(f"%{origin}%")
        if destination:
            domestic_query += " AND f.destination LIKE %s"
            domestic_params.append(f"%{destination}%")
        if departure_date:
            try:
                search_date = datetime.strptime(departure_date, '%Y-%m-%d').date()
                domestic_query += " AND DATE(f.departure) = %s"
                domestic_params.append(search_date)
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        intl_query = """
            SELECT f.*, a.airline_name, at.tier_factor,
            TIMESTAMPDIFF(MINUTE, f.departure, f.arrival) as duration_minutes
            FROM international_flights f
            JOIN airlines a ON f.airline_id = a.airline_id
            JOIN airline_tiers at ON f.airline_id = at.airline_id
            WHERE 1=1
        """
        intl_params = []
        
        if origin:
            intl_query += " AND f.origin LIKE %s"
            intl_params.append(f"%{origin}%")
        if destination:
            intl_query += " AND f.destination LIKE %s"
            intl_params.append(f"%{destination}%")
        if departure_date:
            try:
                search_date = datetime.strptime(departure_date, '%Y-%m-%d').date()
                intl_query += " AND DATE(f.departure) = %s"
                intl_params.append(search_date)
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        if sort_by == 'duration':
            domestic_query += " ORDER BY duration_minutes"
            intl_query += " ORDER BY duration_minutes"
        else:
            domestic_query += " ORDER BY f.base_fare"
            intl_query += " ORDER BY f.base_fare"
        
        if sort_order.lower() == 'desc':
            domestic_query += " DESC"
            intl_query += " DESC"
        
        cursor.execute(domestic_query, domestic_params)
        domestic_flights = cursor.fetchall()
        
        cursor.execute(intl_query, intl_params)
        international_flights = cursor.fetchall()
        
        if include_pricing:
            domestic_results = []
            for flight in domestic_flights:
                pricing_result = calculate_dynamic_price(
                    base_fare=float(flight['base_fare']),
                    total_seats=int(flight['total_seats']),
                    seats_available=int(flight['seats_available']),
                    departure_time=flight['departure'],
                    tier_factor=float(flight['tier_factor'])
                )
                flight_data = dict(flight)
                flight_data['dynamic_price'] = pricing_result['new_price']
                flight_data['price_increase'] = pricing_result['new_price'] - float(flight['base_fare'])
                domestic_results.append(flight_data)
            
            intl_results = []
            for flight in international_flights:
                pricing_result = calculate_dynamic_price(
                    base_fare=float(flight['base_fare']),
                    total_seats=int(flight['total_seats']),
                    seats_available=int(flight['seats_available']),
                    departure_time=flight['departure'],
                    tier_factor=float(flight['tier_factor'])
                )
                flight_data = dict(flight)
                flight_data['dynamic_price'] = pricing_result['new_price']
                flight_data['price_increase'] = pricing_result['new_price'] - float(flight['base_fare'])
                intl_results.append(flight_data)
        else:
            domestic_results = domestic_flights
            intl_results = international_flights
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "search_criteria": {
                "origin": origin,
                "destination": destination,
                "date": departure_date,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "include_pricing": include_pricing
            },
            "domestic_flights": domestic_results,
            "international_flights": intl_results,
            "total_domestic": len(domestic_results),
            "total_international": len(intl_results),
            "total_found": len(domestic_results) + len(intl_results)
        })
    except Exception as e:
        print(f"❌ Error in search_flights endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

# ============================================
# API ROUTES - AIRLINES
# ============================================
@app.route("/airlines")
def get_airlines():
    """Get all airlines"""
    try:
        print("Fetching airlines...")
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM airlines ORDER BY airline_name")
        airlines = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({"airlines": airlines, "total": len(airlines)})
    except Exception as e:
        print(f"Error in get_airlines endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/airlines/tiers")
def get_airline_tiers():
    """Get airline tiers"""
    try:
        print("Fetching airline tiers...")
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT at.airline_id, a.airline_name, at.tier_level, at.tier_factor
            FROM airline_tiers at
            JOIN airlines a ON at.airline_id = a.airline_id
            ORDER BY at.tier_factor DESC
        """)
        tiers = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({"airline_tiers": tiers, "total": len(tiers)})
    except Exception as e:
        print(f"Error in get_airline_tiers endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

# ============================================
# API ROUTES - BOOKINGS
# ============================================
@app.route("/bookings")
def get_bookings():
    """Get all bookings"""
    try:
        print("Fetching bookings...")
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, p.full_name, p.email, p.contact_no
            FROM bookings b
            JOIN passengers p ON b.passenger_id = p.passenger_id
            ORDER BY b.booking_date DESC
        """)
        bookings = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({"bookings": bookings, "total": len(bookings)})
    except Exception as e:
        print(f"Error in get_bookings endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/bookings/create", methods=['POST'])
def create_booking():
    """Create booking - FIXED VERSION"""
    try:
        from models.booking_engine import (
            validate_booking_data, check_seat_availability,
            calculate_fare, simulate_payment, generate_pnr, check_visa_requirement
        )
        
        data = request.get_json()
        
        is_valid, message = validate_booking_data(data)
        if not is_valid:
            return jsonify({"error": message}), 400
        
        flight_type = data['flight_type']
        flight_id = data['flight_id']
        payment_info = data['payment_info']
        
        # FIXED: Check for 'passengers' first
        passengers_to_book = []
        if 'passengers' in data and isinstance(data['passengers'], list):
            passengers_to_book = data['passengers']
        elif 'passenger_info' in data and 'seat_no' in data:
            passengers_to_book = [{"passenger_info": data['passenger_info'], "seat_no": data['seat_no']}]
        else:
            return jsonify({"error": "No passenger data provided"}), 400
        
        for p in passengers_to_book:
            seat_no = p.get('seat_no') or p.get('seatno')
            if not seat_no:
                return jsonify({"error": "Missing seat number for passenger"}), 400
                
            seat_available, seat_message = check_seat_availability(flight_type, flight_id, seat_no)
            if not seat_available:
                return jsonify({"error": f"Seat {seat_no}: {seat_message}"}), 400
        
        for p in passengers_to_book:
            if flight_type == 'INTERNATIONAL':
                passenger_info = p.get('passenger_info') or p
                visa_ok, visa_message = check_visa_requirement(flight_type, flight_id, passenger_info)
                if not visa_ok:
                    fullname = passenger_info.get('fullname') or passenger_info.get('full_name', 'Unknown')
                    return jsonify({"error": f"Visa check failed for {fullname}: {visa_message}"}), 400
        
        fare_per_seat, fare_message = calculate_fare(flight_type, flight_id, apply_dynamic_pricing=True)
        if fare_per_seat is None:
            return jsonify({"error": fare_message}), 400
        
        total_fare = fare_per_seat * len(passengers_to_book)
        
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("START TRANSACTION")
            
            pnr = generate_pnr()
            cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE pnr_code = %s", (pnr,))
            while cursor.fetchone()['count'] > 0:
                pnr = generate_pnr()
                cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE pnr_code = %s", (pnr,))
            
            booking_ids = []
            
            for p in passengers_to_book:
                passenger_info = p.get('passenger_info') or p
                seat_no = p.get('seat_no') or p.get('seatno')
                
                email = passenger_info.get('email')
                cursor.execute("SELECT passenger_id FROM passengers WHERE email = %s", (email,))
                passenger = cursor.fetchone()
                
                if passenger:
                    passenger_id = passenger['passenger_id']
                else:
                    # FIXED: Map visa_status
                    visa_status_raw = passenger_info.get('visa_status', 'N/A')
                    if isinstance(visa_status_raw, str):
                        visa_status_lower = visa_status_raw.lower().strip()
                        if visa_status_lower in ['approved', 'valid', 'active']:
                            visa_status_value = 'Valid'
                        elif visa_status_lower in ['expired', 'rejected', 'denied']:
                            visa_status_value = 'Expired'
                        else:
                            visa_status_value = 'N/A'
                    else:
                        visa_status_value = 'N/A'
                    
                    cursor.execute(
                        """
                        INSERT INTO passengers (full_name, nationality, passport_no, visa_status, contact_no, email)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            passenger_info.get('fullname') or passenger_info.get('full_name'),
                            passenger_info.get('nationality', 'Indian'),
                            passenger_info.get('passport_no'),
                            visa_status_value,
                            passenger_info.get('contactno') or passenger_info.get('contact_no'),
                            email
                        ),
                    )
                    passenger_id = cursor.lastrowid
                
                cursor.execute("""
                    SELECT COUNT(*) as count FROM bookings
                    WHERE flight_type = %s AND flight_ref_id = %s AND seat_no = %s AND status != 'CANCELLED'
                    FOR UPDATE
                """, (flight_type, flight_id, seat_no))
                
                result = cursor.fetchone()
                if result['count'] > 0:
                    conn.rollback()
                    cursor.close()
                    conn.close()
                    return jsonify({"error": f"Seat {seat_no} no longer available"}), 409
                
                cursor.execute(
                    """
                    INSERT INTO bookings (passenger_id, flight_type, flight_ref_id, seat_no, status, pnr_code, booking_amount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (passenger_id, flight_type, flight_id, seat_no, 'CONFIRMED', pnr, fare_per_seat),
                )
                booking_ids.append(cursor.lastrowid)
            
            payment_result = simulate_payment(total_fare, payment_info['payment_mode'])
            if payment_result['status'] != 'SUCCESS':
                conn.rollback()
                cursor.close()
                conn.close()
                return jsonify({"error": "Payment failed", "payment_details": payment_result}), 402
            
            cursor.execute(
                """
                INSERT INTO payments (booking_id, amount, payment_mode, status, transaction_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    booking_ids[0],
                    total_fare,
                    payment_info['payment_mode'],
                    payment_result['status'],
                    payment_result.get('transaction_id'),
                ),
            )
            
            seats_to_reduce = len(passengers_to_book)
            if flight_type == 'DOMESTIC':
                cursor.execute(
                    """
                    UPDATE domestic_flights
                    SET seats_available = seats_available - %s
                    WHERE flight_id = %s
                    """,
                    (seats_to_reduce, flight_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE international_flights
                    SET seats_available = seats_available - %s
                    WHERE intl_id = %s
                    """,
                    (seats_to_reduce, flight_id),
                )
            
            conn.commit()
            
            cursor.execute("""
                SELECT b.*, p.full_name, p.email, p.contact_no, pay.transaction_id
                FROM bookings b
                JOIN passengers p ON b.passenger_id = p.passenger_id
                LEFT JOIN payments pay ON b.booking_id = pay.booking_id
                WHERE b.pnr_code = %s
            """, (pnr,))
            
            booking_details = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                "status": "success",
                "message": f"Booking confirmed for {len(passengers_to_book)} passenger(s)",
                "booking_ids": booking_ids,
                "pnr": pnr,
                "bookings": booking_details,
                "total_fare": total_fare,
                "fare_per_seat": fare_per_seat,
                "payment_status": payment_result['status'],
                "transaction_id": payment_result.get('transaction_id')
            }), 201
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            print(f"❌ Error in booking transaction: {e}")
            return jsonify({"error": f"Booking failed: {str(e)}"}), 500
            
    except Exception as e:
        print(f"❌ Error in create_booking endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/bookings/<int:booking_id>", methods=['GET'])
def get_booking(booking_id):
    """Get booking by ID"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, p.full_name, p.email, p.contact_no, pay.amount, pay.payment_mode, pay.status as payment_status
            FROM bookings b
            JOIN passengers p ON b.passenger_id = p.passenger_id
            LEFT JOIN payments pay ON b.booking_id = pay.booking_id
            WHERE b.booking_id = %s
        """, (booking_id,))
        booking = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not booking:
            return jsonify({"error": "Booking not found"}), 404
        
        return jsonify({"booking": booking})
    except Exception as e:
        print(f"❌ Error in get_booking endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/bookings/pnr/<pnr_code>", methods=['GET'])
def get_booking_by_pnr(pnr_code):
    """Get booking by PNR"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, p.full_name, p.email, p.contact_no, pay.amount, pay.payment_mode, pay.status as payment_status
            FROM bookings b
            JOIN passengers p ON b.passenger_id = p.passenger_id
            LEFT JOIN payments pay ON b.booking_id = pay.booking_id
            WHERE b.pnr_code = %s
        """, (pnr_code,))
        booking = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not booking:
            return jsonify({"error": "Booking not found"}), 404
        
        return jsonify({"booking": booking})
    except Exception as e:
        print(f"❌ Error in get_booking_by_pnr endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/bookings/<int:booking_id>/cancel", methods=['POST'])
def cancel_booking(booking_id):
    """Cancel booking"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("START TRANSACTION")
        
        cursor.execute("SELECT b.* FROM bookings b WHERE b.booking_id = %s", (booking_id,))
        booking = cursor.fetchone()
        
        if not booking:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({"error": "Booking not found"}), 404
        
        if booking['status'] == 'CANCELLED':
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({"error": "Booking already cancelled"}), 400
        
        cursor.execute("UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = %s", (booking_id,))
        
        if booking['flight_type'] == 'DOMESTIC':
            cursor.execute("UPDATE domestic_flights SET seats_available = seats_available + 1 WHERE flight_id = %s", (booking['flight_ref_id'],))
        else:
            cursor.execute("UPDATE international_flights SET seats_available = seats_available + 1 WHERE intl_id = %s", (booking['flight_ref_id'],))
        
        cursor.execute("UPDATE payments SET status = 'REFUNDED' WHERE booking_id = %s", (booking_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Booking cancelled successfully",
            "booking_id": booking_id,
            "refund_status": "Processed"
        })
    except Exception as e:
        conn.rollback()
        print(f"❌ Error in cancel_booking endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/bookings/passenger/<int:passenger_id>", methods=['GET'])
def get_passenger_bookings(passenger_id):
    """Get all bookings for passenger"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, p.full_name, p.email, pay.amount, pay.payment_mode, pay.status as payment_status
            FROM bookings b
            JOIN passengers p ON b.passenger_id = p.passenger_id
            LEFT JOIN payments pay ON b.booking_id = pay.booking_id
            WHERE b.passenger_id = %s
            ORDER BY b.booking_date DESC
        """, (passenger_id,))
        bookings = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({"bookings": bookings, "total": len(bookings)})
    except Exception as e:
        print(f"❌ Error in get_passenger_bookings endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/bookings/check-seat", methods=['GET'])
def check_seat():
    """Check seat availability"""
    try:
        from models.booking_engine import check_seat_availability
        
        flight_type = request.args.get('flight_type')
        flight_id = request.args.get('flight_id', type=int)
        seat_no = request.args.get('seat_no')
        
        if not all([flight_type, flight_id, seat_no]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        available, message = check_seat_availability(flight_type, flight_id, seat_no)
        
        return jsonify({
            "available": available,
            "message": message,
            "flight_type": flight_type,
            "flight_id": flight_id,
            "seat_no": seat_no
        })
    except Exception as e:
        print(f"❌ Error in check_seat endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/bookings/calculate-fare", methods=['POST'])
def calculate_booking_fare():
    """Calculate fare"""
    try:
        from models.booking_engine import calculate_fare
        
        data = request.get_json()
        flight_type = data.get('flight_type')
        flight_id = data.get('flight_id')
        apply_dynamic = data.get('apply_dynamic_pricing', True)
        
        if not flight_type or not flight_id:
            return jsonify({"error": "Missing flight_type or flight_id"}), 400
        
        fare, message = calculate_fare(flight_type, flight_id, apply_dynamic_pricing=apply_dynamic)
        
        if fare is None:
            return jsonify({"error": message}), 400
        
        return jsonify({
            "fare": fare,
            "message": message,
            "flight_type": flight_type,
            "flight_id": flight_id,
            "dynamic_pricing_applied": apply_dynamic
        })
    except Exception as e:
        print(f"❌ Error in calculate_booking_fare endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

# ============================================
# API ROUTES - OTHER DATA
# ============================================
@app.route("/passengers")
def get_passengers():
    """Get all passengers"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM passengers ORDER BY full_name")
        passengers = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({"passengers": passengers, "total": len(passengers)})
    except Exception as e:
        print(f"Error in get_passengers endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/payments")
def get_payments():
    """Get all payments"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, b.flight_type, b.flight_ref_id, pass.full_name
            FROM payments p
            JOIN bookings b ON p.booking_id = b.booking_id
            JOIN passengers pass ON b.passenger_id = pass.passenger_id
            ORDER BY p.payment_date DESC
        """)
        payments = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({"payments": payments, "total": len(payments)})
    except Exception as e:
        print(f"Error in get_payments endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/fare-history")
def get_fare_history():
    """Get fare history"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM fare_history ORDER BY timestamp DESC")
        fare_history = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({"fare_history": fare_history, "total": len(fare_history)})
    except Exception as e:
        print(f"Error in get_fare_history endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/visa-checks")
def get_visa_checks():
    """Get visa checks"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT vc.*, p.full_name, p.passport_no, p.visa_status
            FROM visa_checks vc
            JOIN passengers p ON vc.passenger_id = p.passenger_id
            ORDER BY vc.verification_date DESC
        """)
        visa_checks = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({"visa_checks": visa_checks, "total": len(visa_checks)})
    except Exception as e:
        print(f"Error in get_visa_checks endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/pricing/bulk-calculate")
def bulk_calculate_pricing():
    """Calculate bulk pricing"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT f.*, a.airline_name, at.tier_factor
            FROM domestic_flights f
            JOIN airlines a ON f.airline_id = a.airline_id
            JOIN airline_tiers at ON f.airline_id = at.airline_id
        """)
        domestic_flights = cursor.fetchall()
        
        cursor.execute("""
            SELECT f.*, a.airline_name, at.tier_factor
            FROM international_flights f
            JOIN airlines a ON f.airline_id = a.airline_id
            JOIN airline_tiers at ON f.airline_id = at.airline_id
        """)
        international_flights = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        domestic_pricing = []
        for flight in domestic_flights:
            pricing_result = calculate_dynamic_price(
                base_fare=float(flight['base_fare']),
                total_seats=int(flight['total_seats']),
                seats_available=int(flight['seats_available']),
                departure_time=flight['departure'],
                tier_factor=float(flight['tier_factor'])
            )
            base_fare_float = float(flight['base_fare'])
            domestic_pricing.append({
                "flight_id": flight['flight_id'],
                "flight_no": flight['flight_no'],
                "airline_name": flight['airline_name'],
                "route": f"{flight['origin']} → {flight['destination']}",
                "base_fare": base_fare_float,
                "dynamic_price": pricing_result['new_price'],
                "price_increase": pricing_result['new_price'] - base_fare_float,
                "price_increase_percent": round(((pricing_result['new_price'] - base_fare_float) / base_fare_float) * 100, 2),
                "seat_fill_percentage": round(((flight['total_seats'] - flight['seats_available']) / flight['total_seats']) * 100, 2)
            })
        
        international_pricing = []
        for flight in international_flights:
            pricing_result = calculate_dynamic_price(
                base_fare=float(flight['base_fare']),
                total_seats=int(flight['total_seats']),
                seats_available=int(flight['seats_available']),
                departure_time=flight['departure'],
                tier_factor=float(flight['tier_factor'])
            )
            base_fare_float = float(flight['base_fare'])
            international_pricing.append({
                "flight_id": flight['intl_id'],
                "flight_no": flight['flight_no'],
                "airline_name": flight['airline_name'],
                "route": f"{flight['origin']} → {flight['destination']}",
                "base_fare": base_fare_float,
                "dynamic_price": pricing_result['new_price'],
                "price_increase": pricing_result['new_price'] - base_fare_float,
                "price_increase_percent": round(((pricing_result['new_price'] - base_fare_float) / base_fare_float) * 100, 2),
                "seat_fill_percentage": round(((flight['total_seats'] - flight['seats_available']) / flight['total_seats']) * 100, 2)
            })
        
        return jsonify({
            "domestic_flights": domestic_pricing,
            "international_flights": international_pricing,
            "total_domestic": len(domestic_pricing),
            "total_international": len(international_pricing)
        })
    except Exception as e:
        print(f"Error in bulk_calculate_pricing: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/pricing/dashboard")
def pricing_dashboard():
    """Pricing dashboard"""
    return render_template('pricing_dashboard.html')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)








