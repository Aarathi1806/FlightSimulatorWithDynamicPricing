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

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)





