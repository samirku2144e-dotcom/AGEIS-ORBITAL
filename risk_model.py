import numpy as np


def compute_relative_velocity(v1, v2):
    """
    Compute relative velocity magnitude between two satellites.
    """

    vel1 = np.array([v1["vx"], v1["vy"], v1["vz"]])
    vel2 = np.array([v2["vx"], v2["vy"], v2["vz"]])

    return np.linalg.norm(vel1 - vel2)


def compute_risk(distance, relative_velocity):
    """
    Calculate collision risk score.

    distance → km
    velocity → km/s
    """

    if distance <= 0:
        return 1.0

    # Distance factor
    distance_factor = min(1.0, 1 / distance)

    # Velocity factor
    velocity_factor = min(1.0, relative_velocity / 10)

    # Combine both
    risk = (0.7 * distance_factor) + (0.3 * velocity_factor)

    return round(risk, 3)


def evaluate_collision_risk(obj1, obj2, distance):
    """
    Evaluate collision risk between two satellites.
    """

    relative_velocity = compute_relative_velocity(
        obj1["velocity"],
        obj2["velocity"]
    )

    risk_score = compute_risk(distance, relative_velocity)

    return {
        "satellite_1": obj1["name"],
        "satellite_2": obj2["name"],
        "distance_km": float(distance),
        "relative_velocity": float(relative_velocity),
        "risk_score": risk_score
    }