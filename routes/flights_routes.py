# routes/flights_routes.py
from fastapi import APIRouter, HTTPException
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.queries import get_domestic_flights, get_international_flights

router = APIRouter(
    prefix="/flights",
    tags=["Flights"]
)

@router.get("/domestic")
def domestic_flights():
    try:
        print("Fetching domestic flights...")
        flights = get_domestic_flights()
        print(f"Retrieved {len(flights)} flights")
        
        if not flights:
            return {"message": "No domestic flights found", "domestic_flights": []}
        
        return {"domestic_flights": flights}
    except Exception as e:
        print(f"Error in domestic_flights endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/international")
def international_flights():
    try:
        print("Fetching international flights...")
        flights = get_international_flights()
        print(f"Retrieved {len(flights)} flights")
        
        if not flights:
            return {"message": "No international flights found", "international_flights": []}
        
        return {"international_flights": flights}
    except Exception as e:
        print(f"Error in international_flights endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/all")
def all_flights():
    try:
        print(" Fetching all flights...")
        domestic = get_domestic_flights()
        international = get_international_flights()
        
        return {
            "domestic_flights": domestic,
            "international_flights": international,
            "total_domestic": len(domestic),
            "total_international": len(international)
        }
    except Exception as e:
        print(f"Error in all_flights endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")








