import requests

def generate_aegis_fleet(count=100):
    """Generates offline fallback satellites if CelesTrak blocks us."""
    fleet = ""
    for i in range(count):
        name = f"AEGIS-DEFENDER-{i:03d}"
        line1 = f"1 99{i:03d}U 24001A   24087.50000000  .00000000  00000-0  00000-0 0  9999"
        raan = (i * (360.0 / count)) % 360.0
        ma = (i * 45.0) % 360.0 
        raan_str = f"{raan:8.4f}".rjust(8, ' ')
        ma_str = f"{ma:8.4f}".rjust(8, ' ')
        line2 = f"2 99{i:03d}  51.6415 {raan_str} 0004812  30.0000 {ma_str} 15.50000000000000"
        fleet += f"{name}\n{line1}\n{line2}\n"
    return fleet

def fetch_tle_data():
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        print("PULSE: Requesting visual satellite grid...")
        response = requests.get(url, headers=headers, timeout=5)
        
        # FIX: Explicitly check for TLE markers ('1 ' and '2 ') instead of just character length
        if response.status_code == 200 and '\n1 ' in response.text and '\n2 ' in response.text:
            print("PULSE: Live grid secured.")
            return response.text
        else:
            print("PULSE: Firewall/HTML detected. Deploying 100-unit offline AEGIS Constellation.")
            return generate_aegis_fleet(100)
    except Exception:
        print("PULSE: Network down. Deploying 100-unit offline AEGIS Constellation.")
        return generate_aegis_fleet(100)