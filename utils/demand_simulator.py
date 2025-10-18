import random

def simulate_demand():
    """
    Simulates market demand dynamically.
    Returns one of ['Low', 'Medium', 'High'] randomly.
    """
    return random.choice(['Low', 'Medium', 'High'])
