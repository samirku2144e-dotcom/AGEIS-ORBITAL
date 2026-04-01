from flask import Flask, jsonify
from flask_cors import CORS
import sys
import random
import time
import math
from datetime import datetime, timedelta

try:
    from tle_fetcher import fetch_tle_data
    from tle_parser import parse_tle_data
    from collision_detection import detect_collisions, predict_collision_point 
    from risk_model import evaluate_collision_risk
    from sgp4.api import jday
except ImportError as e:
    print(f"CRITICAL ERROR: {e}")
    sys.exit(1)

app = Flask(__name__)
CORS(app)

SATELLITES = []
MANEUVER_STATE = {}
PERSISTENT_DEBRIS = []
DESTROYED_SATELLITES = set()
RECENT_DESTRUCTIONS = []

TIME_WARP = 50.0  
REAL_START_TIME = None
SIM_START_TIME = None
LAST_API_CALL = None
GM_EARTH = 398600.4418 

def spawn_fragmentation_cloud(base_name, position, velocity):
    """Generates an expanding spherical cloud of debris."""
    is_frag = "FRAG" in base_name
    frag_count = 4 if is_frag else 25 # Fewer frags for debris-on-debris to prevent CPU death
    new_debris = []
    
    for _ in range(frag_count):
        # Calculate random spherical direction
        u = random.random()
        v_rand = random.random()
        theta = 2 * math.pi * u
        phi = math.acos(2 * v_rand - 1)
        
        # Delta-V burst (0.2 to 1.5 km/s outward)
        speed = random.uniform(0.2, 1.5)
        
        dx = speed * math.sin(phi) * math.cos(theta)
        dy = speed * math.sin(phi) * math.sin(theta)
        dz = speed * math.cos(phi)
        
        new_debris.append({
            "name": f"FRAG-{random.randint(10000, 999999)}",
            "position": {
                "x": position['x'] + (dx * 5), 
                "y": position['y'] + (dy * 5), 
                "z": position['z'] + (dz * 5)
            },
            "velocity": {
                "vx": velocity['vx'] + dx,
                "vy": velocity['vy'] + dy,
                "vz": velocity['vz'] + dz
            }
        })
    return new_debris

@app.before_request
def init_data():
    global SATELLITES, REAL_START_TIME, SIM_START_TIME, PERSISTENT_DEBRIS, LAST_API_CALL
    if not SATELLITES:
        try:
            raw = fetch_tle_data()
            SATELLITES = parse_tle_data(raw)[:300] 
        except Exception as e:
            print(f"Error parsing data: {e}")
            SATELLITES = []

        if not SATELLITES:
            print("CRITICAL: Injecting Fallback Constellation.")
            from tle_fetcher import generate_aegis_fleet
            SATELLITES = parse_tle_data(generate_aegis_fleet(100))[:300]

        REAL_START_TIME = time.time()
        LAST_API_CALL = time.time()
        
        if SATELLITES:
            sat = SATELLITES[0]
            year = sat.satrec.epochyr
            full_year = 2000 + year if year < 57 else 1900 + year
            base_date = datetime(full_year, 1, 1)
            SIM_START_TIME = base_date + timedelta(days=sat.satrec.epochdays - 1)
        else:
            SIM_START_TIME = datetime.utcnow()

@app.route('/api/orbital-data')
def get_orbital():
    global PERSISTENT_DEBRIS, DESTROYED_SATELLITES, RECENT_DESTRUCTIONS, LAST_API_CALL
    
    current_destructions = list(RECENT_DESTRUCTIONS)
    RECENT_DESTRUCTIONS.clear()
    
    now = time.time()
    elapsed = now - REAL_START_TIME
    dt_seconds = (now - LAST_API_CALL) * TIME_WARP
    LAST_API_CALL = now
    
    sim_now = SIM_START_TIME + timedelta(seconds=elapsed * TIME_WARP)
    jd, fr = jday(sim_now.year, sim_now.month, sim_now.day, sim_now.hour, sim_now.minute, sim_now.second + sim_now.microsecond / 1e6)
    
    pos = []
    for sat in SATELLITES:
        if sat.name in DESTROYED_SATELLITES:
            continue
        e, r, v = sat.satrec.sgp4(jd, fr)
        if e == 0: 
            pos.append({
                "name": sat.name,
                "position": {"x": float(r[0]), "y": float(r[1]), "z": float(r[2])},
                "velocity": {"vx": float(v[0]), "vy": float(v[1]), "vz": float(v[2])}
            })

    # Propagate existing debris physics
    active_debris = []
    steps = max(1, int(dt_seconds / 5)) 
    sub_dt = dt_seconds / steps
    
    for _ in range(steps):
        for d in PERSISTENT_DEBRIS:
            if d['name'] in DESTROYED_SATELLITES:
                continue
            r_mag = (d["position"]["x"]**2 + d["position"]["y"]**2 + d["position"]["z"]**2)**0.5
            if r_mag > 0:
                ax = -GM_EARTH * d["position"]["x"] / (r_mag**3)
                ay = -GM_EARTH * d["position"]["y"] / (r_mag**3)
                az = -GM_EARTH * d["position"]["z"] / (r_mag**3)
                d["velocity"]["vx"] += ax * sub_dt
                d["velocity"]["vy"] += ay * sub_dt
                d["velocity"]["vz"] += az * sub_dt
            d["position"]["x"] += d["velocity"]["vx"] * sub_dt
            d["position"]["y"] += d["velocity"]["vy"] * sub_dt
            d["position"]["z"] += d["velocity"]["vz"] * sub_dt

    for d in PERSISTENT_DEBRIS:
        if d['name'] not in DESTROYED_SATELLITES:
            active_debris.append(d)

    PERSISTENT_DEBRIS = active_debris
    all_objects = pos + PERSISTENT_DEBRIS
    
    for p in all_objects:
        if p['name'] in MANEUVER_STATE:
            offset = MANEUVER_STATE[p['name']]
            dist = (p['position']['x']**2 + p['position']['y']**2 + p['position']['z']**2)**0.5
            if dist > 0:
                factor = (dist + offset) / dist
                p['position']['x'] *= factor
                p['position']['y'] *= factor
                p['position']['z'] *= factor
                
    raw_collisions = detect_collisions(all_objects, threshold_km=800.0) 
    threats = []
    new_spawned_debris = []
    
    for c in raw_collisions:
        sat1 = c['satellite_1']
        sat2 = c['satellite_2']
        
        is_frag1 = "FRAG" in sat1
        is_frag2 = "FRAG" in sat2
        
        hitbox = 5.0 if (is_frag1 and is_frag2) else 25.0
        
        if c['distance_km'] < hitbox:
            if sat1 not in DESTROYED_SATELLITES and sat2 not in DESTROYED_SATELLITES:
                DESTROYED_SATELLITES.add(sat1)
                DESTROYED_SATELLITES.add(sat2)
                current_destructions.extend([sat1, sat2])
                
                obj1 = next((s for s in all_objects if s['name'] == sat1), None)
                obj2 = next((s for s in all_objects if s['name'] == sat2), None)
                
                if obj1: new_spawned_debris.extend(spawn_fragmentation_cloud(sat1, obj1['position'], obj1['velocity']))
                if obj2: new_spawned_debris.extend(spawn_fragmentation_cloud(sat2, obj2['position'], obj2['velocity']))
        else:
            if sat1 in DESTROYED_SATELLITES or sat2 in DESTROYED_SATELLITES:
                continue
            obj1 = next((s for s in all_objects if s['name'] == sat1), None)
            obj2 = next((s for s in all_objects if s['name'] == sat2), None)
            if obj1 and obj2:
                threat = evaluate_collision_risk(obj1, obj2, c['distance_km'])
                try:
                    tca = predict_collision_point(obj1, obj2, lookahead_sec=600)
                    threat['tca'] = round(tca) if tca else "IMMINENT"
                except:
                    threat['tca'] = "IMMINENT"
                threats.append(threat)
    
    PERSISTENT_DEBRIS.extend(new_spawned_debris)
    
    # FIX: Ensure the payload includes the NEW debris spawned in this exact frame
    final_payload = pos + [d for d in PERSISTENT_DEBRIS if d['name'] not in DESTROYED_SATELLITES]
            
    return jsonify({
        "satellites": final_payload,
        "collisions": sorted(threats, key=lambda x: x['risk_score'], reverse=True),
        "destroyed": current_destructions 
    })

@app.route('/api/maneuver/<path:name>/<m_type>')
def do_maneuver(name, m_type):
    offset = 2000.0 if m_type == 'prograde' else -1200.0 if m_type == 'retrograde' else 2500.0
    MANEUVER_STATE[name] = MANEUVER_STATE.get(name, 0) + offset
    return jsonify({"status": f"{m_type} Successful"})

@app.route('/api/fake-collision/<path:t1>/<path:t2>')
def trigger_fake_collision_exact(t1, t2):
    global DESTROYED_SATELLITES, RECENT_DESTRUCTIONS, PERSISTENT_DEBRIS
    
    target_names = [t1, t2]
    now = time.time()
    elapsed = now - REAL_START_TIME
    sim_now = SIM_START_TIME + timedelta(seconds=elapsed * TIME_WARP)
    jd, fr = jday(sim_now.year, sim_now.month, sim_now.day, sim_now.hour, sim_now.minute, sim_now.second + sim_now.microsecond / 1e6)
    
    for t_name in target_names:
        if t_name not in DESTROYED_SATELLITES:
            DESTROYED_SATELLITES.add(t_name)
            RECENT_DESTRUCTIONS.append(t_name)
            
            sat_obj = next((s for s in SATELLITES if s.name == t_name), None)
            r, v = None, None
            
            if sat_obj:
                e, r_sgp4, v_sgp4 = sat_obj.satrec.sgp4(jd, fr)
                if e == 0:
                    r, v = r_sgp4, v_sgp4
            else:
                deb_obj = next((d for d in PERSISTENT_DEBRIS if d['name'] == t_name), None)
                if deb_obj:
                    r = [deb_obj['position']['x'], deb_obj['position']['y'], deb_obj['position']['z']]
                    v = [deb_obj['velocity']['vx'], deb_obj['velocity']['vy'], deb_obj['velocity']['vz']]
            
            if r and v:
                pos_dict = {'x': r[0], 'y': r[1], 'z': r[2]}
                vel_dict = {'vx': v[0], 'vy': v[1], 'vz': v[2]}
                PERSISTENT_DEBRIS.extend(spawn_fragmentation_cloud(t_name, pos_dict, vel_dict))
            
    return jsonify({"status": "Collision triggered", "victim": t1})

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)