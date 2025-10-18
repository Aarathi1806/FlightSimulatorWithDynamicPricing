Flight Simulator API
A Flight Simulator API built with Flask that manages flights, airlines, bookings, passengers, and dynamic pricing simulation. This project uses a MySQL database with tables for domestic & international flights, bookings, passengers, airlines, payments, fare history, and visa checks.
flight-simulator/
│
├── app.py
├── flight_simulator.sql
├── database/
│   └── db_config.py
├── models/
│   ├── queries.py
│   ├── pricing_engine.py
|--- utils/
│   ── demand_simulator.py
├── templates/
│   └── pricing_dashboard.html
├── .gitignore
└── README.md

