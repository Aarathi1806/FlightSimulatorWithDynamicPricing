from datetime import datetime
import random

def calculate_dynamic_price(base_fare, total_seats, seats_available, departure_time, tier_factor=0.0):
    seat_fill_ratio = (total_seats - seats_available) / total_seats
    seat_factor = seat_fill_ratio * 0.25  

    now = datetime.now()
    days_left = (departure_time - now).days
    if days_left <= 1:
        time_factor = 0.30  
    elif days_left <= 7:
        time_factor = 0.15
    else:
        time_factor = 0.05

    demand_factor = random.uniform(-0.05, 0.25)  
    new_price = base_fare * (1 + seat_factor + time_factor + demand_factor + tier_factor)
    new_price = round(new_price, 2)

    return {
        "new_price": new_price,
        "seat_factor": seat_factor,
        "time_factor": time_factor,
        "demand_factor": demand_factor
    }

def simulate_demand():
    return random.choice(['Low', 'Medium', 'High'])

