from datetime import datetime
from sgp4.api import jday
import numpy as np

def compute_satellite_position(sat_obj):
    """
    Calculates the current X, Y, Z coordinates using SGP4.
    Used by position_generator.py
    """
    try:
        now = datetime.utcnow()
        # Create Julian Date for the current moment
        jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second)
        
        # Core SGP4 calculation
        e, r, v = sat_obj.satrec.sgp4(jd, fr)
        
        if e == 0:
            return {
                "name": str(sat_obj.name),
                "position": {"x": float(r[0]), "y": float(r[1]), "z": float(r[2])},
                "velocity": {"vx": float(v[0]), "vy": float(v[1]), "vz": float(v[2])}
            }
        return None
    except Exception as err:
        print(f"Physics Error for {sat_obj.name}: {err}")
        return None

def apply_maneuver(sat_obj, delta_v_kms):
    """
    Applies a tangential thrust (Delta-V) to change the orbit.
    Used by the Maneuver API
    """
    now = datetime.utcnow()
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second)
    
    e, r, v = sat_obj.satrec.sgp4(jd, fr)
    
    if e == 0:
        v_vector = np.array(v)
        speed = np.linalg.norm(v_vector)
        
        # Unit vector of velocity (direction of flight)
        unit_velocity = v_vector / speed
        
        # New velocity = Old velocity + (Direction * extra speed)
        new_v = v_vector + (unit_velocity * delta_v_kms)
        
        return {
            "name": f"{sat_obj.name} [MANEUVERING]",
            "position": {"x": float(r[0]), "y": float(r[1]), "z": float(r[2])},
            "velocity": {"vx": float(new_v[0]), "vy": float(new_v[1]), "vz": float(new_v[2])},
            "is_maneuvering": True
        }
    return None