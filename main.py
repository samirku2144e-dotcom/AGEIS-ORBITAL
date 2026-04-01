from tle_fetcher import fetch_tle_data
from tle_parser import parse_tle_data
from position_generator import generate_positions
from collision_detection import detect_collisions

import time


def main():

    print("Aegis Orbital Monitoring Started")

    # Step 1 — Download orbital data
    raw_data = fetch_tle_data()

    # Step 2 — Parse satellites
    satellites = parse_tle_data(raw_data)

    # Limit satellites for CPU safety
    satellites = satellites[:200]

    print("Satellites loaded:", len(satellites))

    # Step 3 — Continuous monitoring loop
    while True:

        # Generate current positions
        positions = generate_positions(satellites, debris_count=5)

        print("Positions generated:", len(positions))

        # Detect possible collisions
        collisions = detect_collisions(positions)

        print("Potential collisions:", len(collisions))

        if collisions:
            print("WARNING:", collisions[0])

        print("-----")

        # Update every 5 seconds
        time.sleep(5)


if __name__ == "__main__":
    main()