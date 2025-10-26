from datetime import datetime
from flask import Flask, jsonify, render_template
from flask_cors import CORS
from database.db_config import get_connection
from models.pricing_engine import calculate_dynamic_price
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__)
CORS(app)

@app.route("/")
def root():
    return jsonify({"message": "Flight Simulator API is running!"})

@app.route("/test")
def test_db():
    try:
        from database.db_config import get_connection
        conn = get_connection()
        if conn:
            conn.close()
            return jsonify({"status": "Database connected successfully "})
        return jsonify({"status": "Database connection failed "})
    except Exception as e:
        return jsonify({"status": f"Database connection failed - Error: {str(e)}"})

@app.route("/flights/domestic")
def domestic_flights():
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
    try:
        print("📡 Fetching all flights...")
        from models.queries import get_domestic_flights, get_international_flights
        domestic = get_domestic_flights()
        international = get_international_flights()
        
        return jsonify({
            "domestic_flights": domestic,
            "international_flights": international,
            "total_domestic": len(domestic),
            "total_international": len(international)
        })
    except Exception as e:
        print(f"Error in all_flights endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

# Enhanced Flight Search with filtering and sorting
@app.route("/flights/search")
def search_flights():
    """Search flights by origin, destination, date with sorting options"""
    try:
        from flask import request
        from datetime import datetime
        
        # Get query parameters
        origin = request.args.get('origin', '').strip().title()
        destination = request.args.get('destination', '').strip().title()
        departure_date = request.args.get('date', '').strip()
        sort_by = request.args.get('sort', 'price')  # price or duration
        sort_order = request.args.get('order', 'asc')  # asc or desc
        include_pricing = request.args.get('pricing', 'false').lower() == 'true'
        
        print(f"🔍 Searching flights: {origin} → {destination} on {departure_date}")
        
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Build search query for domestic flights
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
        
        # Build search query for international flights
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
        
        # Add sorting
        if sort_by == 'duration':
            domestic_query += " ORDER BY duration_minutes"
            intl_query += " ORDER BY duration_minutes"
        else:  # default to price
            domestic_query += " ORDER BY f.base_fare"
            intl_query += " ORDER BY f.base_fare"
        
        if sort_order.lower() == 'desc':
            domestic_query += " DESC"
            intl_query += " DESC"
        
        # Execute queries
        cursor.execute(domestic_query, domestic_params)
        domestic_flights = cursor.fetchall()
        
        cursor.execute(intl_query, intl_params)
        international_flights = cursor.fetchall()
        
        # Apply dynamic pricing if requested
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

@app.route("/airlines")
def get_airlines():
    try:
        print("Fetching airlines...")
        from database.db_config import get_connection
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
    try:
        print("Fetching airline tiers...")
        from database.db_config import get_connection
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

@app.route("/bookings")
def get_bookings():
    try:
        print("Fetching bookings...")
        from database.db_config import get_connection
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

@app.route("/passengers")
def get_passengers():
    try:
        print("Fetching passengers...")
        from database.db_config import get_connection
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
    try:
        print("Fetching payments...")
        from database.db_config import get_connection
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
    try:
        print("Fetching fare history...")
        from database.db_config import get_connection
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
    try:
        print("Fetching visa checks...")
        from database.db_config import get_connection
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
    try:
        print("Calculating dynamic prices for all flights...")
        from database.db_config import get_connection
        from models.pricing_engine import calculate_dynamic_price
        from datetime import datetime
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
            "total_international": len(international_pricing),
            "summary": {
                "avg_domestic_increase": round(sum(f['price_increase_percent'] for f in domestic_pricing) / len(domestic_pricing), 2) if domestic_pricing else 0,
                "avg_international_increase": round(sum(f['price_increase_percent'] for f in international_pricing) / len(international_pricing), 2) if international_pricing else 0
            }
        })
    except Exception as e:
        print(f"Error in bulk_calculate_pricing endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/pricing/simulate-demand")
def simulate_demand():
    try:
        print("📡 Simulating market demand...")
        from models.pricing_engine import simulate_demand
        
        demand = simulate_demand()
        
        return jsonify({
            "market_demand": demand,
            "timestamp": datetime.now().isoformat(),
            "description": {
                "Low": "Lower prices due to low demand",
                "Medium": "Standard pricing with moderate demand",
                "High": "Higher prices due to high demand"
            }[demand]
        })
    except Exception as e:
        print(f"Error in simulate_demand endpoint: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

# External API Simulation
@app.route("/api/external/schedules")
def external_airline_schedules():
    """Simulate external airline schedule APIs"""
    try:
        print("📡 Simulating external airline schedule API...")
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Simulate external API response format
        cursor.execute("""
            SELECT 
                f.flight_no as flightNumber,
                a.airline_name as airline,
                f.origin as from,
                f.destination as to,
                f.departure as departureTime,
                f.arrival as arrivalTime,
                f.base_fare as basePrice,
                f.total_seats as totalSeats,
                f.seats_available as availableSeats,
                CASE 
                    WHEN f.seats_available < 10 THEN 'LOW'
                    WHEN f.seats_available < 50 THEN 'MEDIUM'
                    ELSE 'HIGH'
                END as availability
            FROM domestic_flights f
            JOIN airlines a ON f.airline_id = a.airline_id
            LIMIT 10
        """)
        domestic_schedules = cursor.fetchall()
        
        cursor.execute("""
            SELECT 
                f.flight_no as flightNumber,
                a.airline_name as airline,
                f.origin as from,
                f.destination as to,
                f.departure as departureTime,
                f.arrival as arrivalTime,
                f.base_fare as basePrice,
                f.total_seats as totalSeats,
                f.seats_available as availableSeats,
                CASE 
                    WHEN f.seats_available < 10 THEN 'LOW'
                    WHEN f.seats_available < 50 THEN 'MEDIUM'
                    ELSE 'HIGH'
                END as availability,
                f.requires_visa as visaRequired
            FROM international_flights f
            JOIN airlines a ON f.airline_id = a.airline_id
            LIMIT 10
        """)
        international_schedules = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "api_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "data": {
                "domestic_schedules": domestic_schedules,
                "international_schedules": international_schedules,
                "total_flights": len(domestic_schedules) + len(international_schedules)
            },
            "metadata": {
                "source": "Flight Simulator External API",
                "last_updated": datetime.now().isoformat(),
                "rate_limit": "1000 requests/hour"
            }
        })
        
    except Exception as e:
        print(f"❌ Error in external airline schedules: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

# Background Process for Demand/Availability Changes
@app.route("/pricing/update-demand")
def update_demand_availability():
    """Background process to simulate demand and availability changes"""
    try:
        print("🔄 Updating demand and availability...")
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        
        # Simulate random seat availability changes
        cursor.execute("""
            UPDATE domestic_flights 
            SET seats_available = GREATEST(0, LEAST(total_seats, 
                seats_available + FLOOR(RAND() * 6) - 3
            ))
            WHERE seats_available > 0
        """)
        domestic_updated = cursor.rowcount
        
        cursor.execute("""
            UPDATE international_flights 
            SET seats_available = GREATEST(0, LEAST(total_seats, 
                seats_available + FLOOR(RAND() * 6) - 3
            ))
            WHERE seats_available > 0
        """)
        intl_updated = cursor.rowcount
        
        # Record fare changes in history
        cursor.execute("""
            INSERT INTO fare_history (flight_type, flight_no, timestamp, old_fare, new_fare, demand_factor, remarks)
            SELECT 
                'DOMESTIC' as flight_type,
                f.flight_no,
                NOW() as timestamp,
                f.base_fare as old_fare,
                f.base_fare * (1 + RAND() * 0.1 - 0.05) as new_fare,
                RAND() * 0.3 as demand_factor,
                CASE 
                    WHEN RAND() > 0.7 THEN 'High demand detected'
                    WHEN RAND() > 0.4 THEN 'Moderate demand'
                    ELSE 'Low demand period'
                END as remarks
            FROM domestic_flights f
            WHERE RAND() < 0.3
            LIMIT 3
        """)
        
        cursor.execute("""
            INSERT INTO fare_history (flight_type, flight_no, timestamp, old_fare, new_fare, demand_factor, remarks)
            SELECT 
                'INTERNATIONAL' as flight_type,
                f.flight_no,
                NOW() as timestamp,
                f.base_fare as old_fare,
                f.base_fare * (1 + RAND() * 0.1 - 0.05) as new_fare,
                RAND() * 0.3 as demand_factor,
                CASE 
                    WHEN RAND() > 0.7 THEN 'High demand detected'
                    WHEN RAND() > 0.4 THEN 'Moderate demand'
                    ELSE 'Low demand period'
                END as remarks
            FROM international_flights f
            WHERE RAND() < 0.3
            LIMIT 3
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "updates": {
                "domestic_flights_updated": domestic_updated,
                "international_flights_updated": intl_updated,
                "fare_history_records": 10
            },
            "message": "Demand and availability successfully updated"
        })
        
    except Exception as e:
        print(f"❌ Error updating demand/availability: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/pricing/dashboard")
def pricing_dashboard():
    """Serve the pricing dashboard HTML page"""
    return render_template('pricing_dashboard.html')

@app.route("/pricing/domestic-data")
def get_domestic_pricing_data():
    """Get domestic flights pricing data as JSON"""
    try:
        from database.db_config import get_connection
        from models.pricing_engine import calculate_dynamic_price
        
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.*, a.airline_name, at.tier_factor
            FROM domestic_flights f 
            JOIN airlines a ON f.airline_id = a.airline_id 
            JOIN airline_tiers at ON f.airline_id = at.airline_id
            LIMIT 5
        """)
        domestic_flights = cursor.fetchall()
        cursor.close()
        conn.close()
        pricing_data = []
        for flight in domestic_flights:
            pricing_result = calculate_dynamic_price(
                base_fare=float(flight['base_fare']),
                total_seats=int(flight['total_seats']),
                seats_available=int(flight['seats_available']),
                departure_time=flight['departure'],
                tier_factor=float(flight['tier_factor'])
            )
            base_fare = float(flight['base_fare'])
            dynamic_price = pricing_result['new_price']
            increase = dynamic_price - base_fare
            increase_percent = round((increase / base_fare) * 100, 1)
            pricing_data.append({
                'flight_id': flight['flight_id'],
                'flight_no': flight['flight_no'],
                'airline_name': flight['airline_name'],
                'origin': flight['origin'],
                'destination': flight['destination'],
                'base_fare': base_fare,
                'dynamic_price': dynamic_price,
                'price_increase': increase,
                'price_increase_percent': increase_percent,
                'total_seats': flight['total_seats'],
                'seats_available': flight['seats_available'],
                'factors': {
                    'seat_factor': round(pricing_result['seat_factor']*100, 1),
                    'time_factor': round(pricing_result['time_factor']*100, 1),
                    'demand_factor': round(pricing_result['demand_factor']*100, 1),
                    'tier_factor': round(float(flight['tier_factor'])*100, 1)
                }
            })
        return jsonify(pricing_data)
    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route("/pricing/international-data")
def get_international_pricing_data():
    """Get international flights pricing data as JSON"""
    try:
        from database.db_config import get_connection
        from models.pricing_engine import calculate_dynamic_price
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.*, a.airline_name, at.tier_factor
            FROM international_flights f 
            JOIN airlines a ON f.airline_id = a.airline_id 
            JOIN airline_tiers at ON f.airline_id = at.airline_id
            LIMIT 5
        """)
        international_flights = cursor.fetchall()
        cursor.close()
        conn.close()
        pricing_data = []
        for flight in international_flights:
            pricing_result = calculate_dynamic_price(
                base_fare=float(flight['base_fare']),
                total_seats=int(flight['total_seats']),
                seats_available=int(flight['seats_available']),
                departure_time=flight['departure'],
                tier_factor=float(flight['tier_factor'])
            )
            base_fare = float(flight['base_fare'])
            dynamic_price = pricing_result['new_price']
            increase = dynamic_price - base_fare
            increase_percent = round((increase / base_fare) * 100, 1)
            pricing_data.append({
                'flight_id': flight['intl_id'],
                'flight_no': flight['flight_no'],
                'airline_name': flight['airline_name'],
                'origin': flight['origin'],
                'destination': flight['destination'],
                'base_fare': base_fare,
                'dynamic_price': dynamic_price,
                'price_increase': increase,
                'price_increase_percent': increase_percent,
                'total_seats': flight['total_seats'],
                'seats_available': flight['seats_available'],
                'factors': {
                    'seat_factor': round(pricing_result['seat_factor']*100, 1),
                    'time_factor': round(pricing_result['time_factor']*100, 1),
                    'demand_factor': round(pricing_result['demand_factor']*100, 1),
                    'tier_factor': round(float(flight['tier_factor'])*100, 1)
                }
            })
        return jsonify(pricing_data)
    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500

# ============================================
# BOOKING WORKFLOW ENDPOINTS
# ============================================

@app.route("/bookings/create", methods=['POST'])
def create_booking():
    """Create a new booking with concurrency control and PNR generation"""
    try:
        from flask import request
        from models.booking_engine import (
            validate_booking_data, check_seat_availability, 
            calculate_fare, simulate_payment, generate_pnr
        )
        
        data = request.get_json()
        
        # Validate input data
        is_valid, message = validate_booking_data(data)
        if not is_valid:
            return jsonify({"error": message}), 400
        
        flight_type = data['flight_type']
        flight_id = data['flight_id']
        seat_no = data['seat_no']
        passenger_info = data['passenger_info']
        payment_info = data['payment_info']
        
        # Check seat availability with concurrency control
        seat_available, seat_message = check_seat_availability(flight_type, flight_id, seat_no)
        if not seat_available:
            return jsonify({"error": seat_message}), 400
        
        # Calculate fare (with dynamic pricing)
        fare, fare_message = calculate_fare(flight_type, flight_id, apply_dynamic_pricing=True)
        if fare is None:
            return jsonify({"error": fare_message}), 400
        
        # Start database transaction for concurrency control
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Lock the seat for booking (transaction isolation level)
            cursor.execute("START TRANSACTION")
            
            # Check seat availability again within transaction (concurrency control)
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
                return jsonify({"error": "Seat no longer available"}), 409
            
            # Check passenger exists or create new passenger
            cursor.execute("""
                SELECT passenger_id FROM passengers WHERE email = %s
            """, (passenger_info['email'],))
            
            passenger = cursor.fetchone()
            
            if passenger:
                passenger_id = passenger['passenger_id']
            else:
                # Create new passenger
                cursor.execute("""
                    INSERT INTO passengers (full_name, nationality, passport_no, visa_status, contact_no, email)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    passenger_info['full_name'],
                    passenger_info.get('nationality', 'Indian'),
                    passenger_info.get('passport_no'),
                    passenger_info.get('visa_status', 'N/A'),
                    passenger_info.get('contact_no'),
                    passenger_info['email']
                ))
                passenger_id = cursor.lastrowid
            
            # Process payment
            payment_result = simulate_payment(fare, payment_info['payment_mode'])
            
            if payment_result['status'] != 'SUCCESS':
                conn.rollback()
                cursor.close()
                conn.close()
                return jsonify({
                    "error": "Payment failed",
                    "payment_details": payment_result
                }), 402
            
            # Create booking
            pnr = generate_pnr()
            
            # Check for PNR uniqueness
            cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE pnr_code = %s", (pnr,))
            while cursor.fetchone()['count'] > 0:
                pnr = generate_pnr()
                cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE pnr_code = %s", (pnr,))
            
            cursor.execute("""
                INSERT INTO bookings (passenger_id, flight_type, flight_ref_id, seat_no, status, pnr_code, booking_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (passenger_id, flight_type, flight_id, seat_no, 'CONFIRMED', pnr, fare))
            
            booking_id = cursor.lastrowid
            
            # Create payment record
            cursor.execute("""
                INSERT INTO payments (booking_id, amount, payment_mode, status, transaction_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                booking_id, 
                fare, 
                payment_info['payment_mode'], 
                payment_result['status'],
                payment_result.get('transaction_id')
            ))
            
            # Update seat availability
            if flight_type == 'DOMESTIC':
                cursor.execute("""
                    UPDATE domestic_flights 
                    SET seats_available = seats_available - 1 
                    WHERE flight_id = %s
                """, (flight_id,))
            else:
                cursor.execute("""
                    UPDATE international_flights 
                    SET seats_available = seats_available - 1 
                    WHERE intl_id = %s
                """, (flight_id,))
            
            # Commit transaction
            conn.commit()
            
            # Fetch booking details
            cursor.execute("""
                SELECT b.*, p.full_name, p.email, pay.transaction_id
                FROM bookings b
                JOIN passengers p ON b.passenger_id = p.passenger_id
                LEFT JOIN payments pay ON b.booking_id = pay.booking_id
                WHERE b.booking_id = %s
            """, (booking_id,))
            
            booking_details = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                "status": "success",
                "message": "Booking confirmed",
                "booking_id": booking_id,
                "pnr": pnr,
                "booking_details": booking_details,
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
    """Get booking details by booking_id"""
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
    """Get booking details by PNR"""
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
    """Cancel a booking and refund payment"""
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Get booking details
        cursor.execute("""
            SELECT b.*
            FROM bookings b
            WHERE b.booking_id = %s
        """, (booking_id,))
        
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
        
        # Update booking status
        cursor.execute("""
            UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = %s
        """, (booking_id,))
        
        # Update seat availability
        if booking['flight_type'] == 'DOMESTIC':
            cursor.execute("""
                UPDATE domestic_flights 
                SET seats_available = seats_available + 1 
                WHERE flight_id = %s
            """, (booking['flight_ref_id'],))
        else:
            cursor.execute("""
                UPDATE international_flights 
                SET seats_available = seats_available + 1 
                WHERE intl_id = %s
            """, (booking['flight_ref_id'],))
        
        # Update payment status to refunded
        cursor.execute("""
            UPDATE payments SET status = 'REFUNDED' WHERE booking_id = %s
        """, (booking_id,))
        
        # Commit transaction
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
    """Get all bookings for a passenger"""
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
    """Check if a specific seat is available"""
    try:
        from flask import request
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
    """Calculate fare for a booking request"""
    try:
        from flask import request
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

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)





