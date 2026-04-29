import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / 'app'))
import database as db
from datetime import datetime

patients = db.get_all_patients()
week_44 = []

for p in patients:
    fbd = p.get('first_booking_date')
    if fbd:
        try:
            dt = datetime.strptime(fbd, '%Y-%m-%d')
            wk = dt.strftime('%G-W%V')
            if wk == '2025-W44':
                if p.get('referral_date') and p.get('vardgaranti_date'):
                    vg = datetime.strptime(p['vardgaranti_date'], '%Y-%m-%d')
                    ref = datetime.strptime(p['referral_date'], '%Y-%m-%d')
                    delay = (vg - ref).days
                    week_44.append({
                        "pn": p.get('personal_number', ''),
                        "name": f"{p.get('first_name', '')} {p.get('last_name', '')}",
                        "ref": p['referral_date'],
                        "vg": p['vardgaranti_date'],
                        "delay": delay
                    })
        except Exception as e:
            pass

week_44.sort(key=lambda x: x['delay'], reverse=True)
print(f"Total valid patients in week 44: {len(week_44)}")
print("-" * 50)
for w in week_44:
    print(f"PN: {w['pn']} | {w['name']} | Ref: {w['ref']} | VG: {w['vg']} | Delay: {w['delay']} days")
