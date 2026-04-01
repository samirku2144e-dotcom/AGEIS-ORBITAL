from orbit_engine import compute_satellite_position
import random


def generate_positions(satellites, debris_count=0):

    positions = []

    # Generate satellite positions
    for sat in satellites:

        result = compute_satellite_position(sat)

        if result:
            positions.append(result)

    # Generate simulated debris near random satellites
    for _ in range(debris_count):

        if not positions:
            break

        target = random.choice(positions)

        debris = {
            "name": "SIM-DEBRIS",
            "position": {
                "x": target["position"]["x"] + random.uniform(-1, 1),
                "y": target["position"]["y"] + random.uniform(-1, 1),
                "z": target["position"]["z"] + random.uniform(-1, 1)
            },
            "velocity": {
                "vx": random.uniform(-8, 8),
                "vy": random.uniform(-8, 8),
                "vz": random.uniform(-8, 8)
            }
        }

        positions.append(debris)

    return positions