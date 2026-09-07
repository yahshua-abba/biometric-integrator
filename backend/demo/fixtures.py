"""Synthetic volume fixtures for the isolated mini Payroll demos."""
from datetime import date, datetime, timedelta


def seed_large_queue(db, employees=300, logs_each=40):
    """Add repeatable volume data without device access or external HTTP calls."""
    conn = db.get_connection()
    given = ['Mara', 'Luis', 'Ana', 'Rafael', 'Elena', 'Marco', 'Isabel', 'Paolo', 'Sofia', 'Diego']
    family = ['Santos', 'Cruz', 'Reyes', 'Garcia', 'Mendoza', 'Ramos', 'Torres', 'Castillo', 'Flores', 'Rivera', 'Navarro', 'Dizon', 'Lopez', 'Bautista', 'Aquino', 'Mercado', 'Villanueva', 'Lim', 'Tan', 'Santiago', 'Salazar', 'Domingo', 'Aguilar', 'Valdez', 'Gonzales', 'Serrano', 'Del Rosario', 'Pascual', 'Soriano', 'De Leon']
    try:
        with conn:
            for n in range(employees):
                code = str(90000 + n)
                existing = conn.execute('SELECT id FROM employee WHERE employee_code=?', (code,)).fetchone()
                if existing:
                    employee_id = existing['id']
                else:
                    employee_id = conn.execute('INSERT INTO employee(backend_id,name,employee_code) VALUES(?,?,?)',
                        (code, f'{given[n % len(given)]} {family[n // len(given) % len(family)]} (demo)', code)).lastrowid
                for i in range(logs_each):
                    day = (date.today() - timedelta(days=i//2)).isoformat()
                    outcome = 'unconfirmed' if i % 5 == 0 else 'failed'
                    reason = 'No confirmation received — check Payroll' if outcome == 'unconfirmed' else (
                        'Employee not found in Payroll' if n % 2 else 'Employee not assigned to branch')
                    sync_id = f'ZK_VOLUME_{code}_{i}'
                    conn.execute('''INSERT OR IGNORE INTO timesheet
                        (sync_id,employee_id,log_type,date,time,status,sync_error_message,sync_error_message_2)
                        VALUES(?,?,?,?,?,'success',?,?)''',
                        (sync_id, employee_id, 'in' if i % 2 == 0 else 'out', day, '08:00' if i % 2 == 0 else '17:00', reason, reason))
                    for slot in (1, 2):
                        conn.execute('''INSERT OR IGNORE INTO delivery_attempt(sync_id,slot,attempted_at,attempts,outcome)
                            VALUES(?,?,?,1,?)''', (sync_id, slot, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), outcome))
        return {'employees': employees, 'attendance_logs': employees * logs_each, 'uploads': employees * logs_each * 2}
    finally:
        conn.close()
