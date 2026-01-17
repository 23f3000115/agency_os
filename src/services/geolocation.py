from geopy.distance import geodesic

# CONFIG: Set your actual office coordinates here
OFFICE_COORDS = (30.1881886, 74.3046929) 
ALLOWED_RADIUS_METERS = 100

def check_geofence(user_lat, user_lon):
    """
    Returns (is_inside: bool, distance: int)
    """
    if user_lat is None or user_lon is None:
        return False, 9999
        
    user_point = (user_lat, user_lon)
    distance = geodesic(OFFICE_COORDS, user_point).meters
    
    is_inside = distance <= ALLOWED_RADIUS_METERS
    return is_inside, int(distance)