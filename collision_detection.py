import numpy as np

def detect_collisions(positions, threshold_km=10.0):
    """
    Scans all active objects and flags any pair within the threshold distance.
    """
    collisions = []
    
    # Nested loop to compare every satellite against every other satellite
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            # Convert positions to numpy arrays for vector math
            p1 = np.array([positions[i]['position']['x'], 
                          positions[i]['position']['y'], 
                          positions[i]['position']['z']])
            
            p2 = np.array([positions[j]['position']['x'], 
                          positions[j]['position']['y'], 
                          positions[j]['position']['z']])
            
            # Calculate Euclidean distance: ||p1 - p2||
            distance = np.linalg.norm(p1 - p2)
            
            if distance < threshold_km:
                # Calculate a Risk Score (0.0 to 1.0)
                # Closer objects have a higher score
                risk_score = round(max(0, 1 - (distance / threshold_km)), 2)
                
                collisions.append({
                    "satellite_1": positions[i]['name'],
                    "satellite_2": positions[j]['name'],
                    "distance_km": float(distance),
                    "risk_score": risk_score
                })
    
    # Sort by highest risk first
    return sorted(collisions, key=lambda x: x['risk_score'], reverse=True)

def predict_collision_point(sat1, sat2, lookahead_sec=300):
    """
    Predicts the Time of Closest Approach (TCA) for two objects.
    """
    p1 = np.array([sat1['position']['x'], sat1['position']['y'], sat1['position']['z']])
    v1 = np.array([sat1['velocity']['vx'], sat1['velocity']['vy'], sat1['velocity']['vz']])
    
    p2 = np.array([sat2['position']['x'], sat2['position']['y'], sat2['position']['z']])
    v2 = np.array([sat2['velocity']['vx'], sat2['velocity']['vy'], sat2['velocity']['vz']])

    dr = p1 - p2
    dv = v1 - v2
    
    # TCA Formula: t = -(dr ⋅ dv) / ||dv||²
    dv_sq = np.dot(dv, dv)
    if dv_sq == 0: return None
    
    t_tca = -np.dot(dr, dv) / dv_sq
    
    if 0 < t_tca < lookahead_sec:
        return t_tca
    return None