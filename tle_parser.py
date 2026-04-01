from sgp4.api import Satrec

class Satellite:
    def __init__(self, name, line1, line2):
        self.name = name
        self.satrec = Satrec.twoline2rv(line1, line2) 

def parse_tle_data(raw_data):
    # Split and remove empty lines to keep the 3-line rhythm
    lines = [l.strip() for l in raw_data.strip().split('\n') if l.strip()]
    satellites = []
    
    # TLEs are 3 lines: Name, Line 1, Line 2
    for i in range(0, len(lines) - 2, 3):
        try:
            name = lines[i]
            l1 = lines[i+1]
            l2 = lines[i+2]
            # Verify these are actual TLE lines
            if l1.startswith('1 ') and l2.startswith('2 '):
                satellites.append(Satellite(name, l1, l2))
        except:
            continue
    return satellites