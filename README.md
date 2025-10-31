FLIGHTSIM - FLIGHT BOOKING SYSTEM

Web-based flight booking application with user authentication, dynamic pricing, 
seat selection, and PNR-based booking management.

DIRECTORY STRUCTURE

flight_simulator/
    app.py
    config.py
    flight_simulator.sql
    database/
        db_config.py
    models/
        pricing_engine.py
        booking_engine.py
        queries.py
    templates/
        base.html
        home.html
        login.html
        signup.html
        search.html
        flights.html
        booking.html
        my_bookings.html
        pricing_dashboard.html
    static/
        styles.css


INSTALLATION

1. Install dependencies
   pip install flask flask-cors mysql-connector-python werkzeug

2. Update config.py with MySQL credentials
   MYSQL_HOST = 'localhost'
   MYSQL_USER = 'root'
   MYSQL_PASSWORD = 'your_password'
   MYSQL_DATABASE = 'flight_simulator'

3. Create MySQL database
   mysql -u root -p < database.sql

4. Run application
   python app.py


WORKFLOW

User → Login/Signup → Home Page → Search/Browse Flights → Select Flight → 
Enter Passenger Details → Confirm Booking → Receive PNR → View Bookings → Logout


KEY FEATURES

PNR Generation: Each booking gets a unique 6-character reference code stored in database

Dynamic Pricing Engine: Calculates real-time prices using factors - seat availability 
percentage, time to departure, airline tier level, and simulated market demand. 
Formula: New Price = Base Fare × (1 + Seat Factor + Time Factor + Demand Factor + Tier Factor)

Authentication: Secure login/signup with password hashing using Werkzeug

Booking Management: Multiple passengers per booking, seat selection, visa verification 
for international flights, cancellation with refund


GIT COMMANDS

git add .
git commit -m "Add flight booking system with authentication and dynamic pricing"
git push origin main


API ENDPOINTS

POST /auth/login, /auth/signup, /auth/logout
GET /auth/check-session
GET /flights/all, /flights/search
POST /bookings/create
GET /bookings/pnr/<pnr_code>
POST /bookings/<id>/cancel


ACCESS APPLICATION

http://localhost:5000 - Redirects to login
http://localhost:5000/ui - Home page after login
http://localhost:5000/ui/search - Search flights
http://localhost:5000/pricing/dashboard - Pricing analytics


