import sqlite3
conn = sqlite3.connect('data/webdoc_patients.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM patients')
print('patients:', c.fetchone()[0])
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('tables:', [r[0] for r in c.fetchall()])
# Sample data
c.execute('SELECT personal_number, first_name, last_name FROM patients LIMIT 5')
for r in c.fetchall():
    print(f'  {r[0]} - {r[1]} {r[2]}')
conn.close()
