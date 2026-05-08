import sqlite3
import os

db_path = os.path.join('instance', 'betterme.db')
print(f'DB path: {os.path.abspath(db_path)}')
print(f'DB exists: {os.path.exists(db_path)}')
print()

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print('=== TABLAS EN LA DB ===')
    for t in tables:
        cursor.execute(f'SELECT COUNT(*) FROM [{t[0]}]')
        count = cursor.fetchone()[0]
        print(f'  {t[0]}: {count} registros')
    
    print()
    print('=== USUARIOS ===')
    cursor.execute('SELECT id, name, email, avatar FROM user')
    users = cursor.fetchall()
    if users:
        for u in users:
            print(f'  ID:{u[0]} | {u[1]} | {u[2]} | avatar:{u[3]}')
    else:
        print('  No hay usuarios registrados')
    
    print()
    print('=== HABITS ===')
    cursor.execute('SELECT id, name, coins, is_custom FROM habit')
    habits = cursor.fetchall()
    if habits:
        for h in habits:
            print(f'  ID:{h[0]} | {h[1]} | coins:{h[2]} | custom:{h[3]}')
    else:
        print('  No hay hábitos')
    
    print()
    print('=== USER_HABIT ===')
    cursor.execute('SELECT * FROM user_habit')
    uhs = cursor.fetchall()
    if uhs:
        for uh in uhs:
            print(f'  {uh}')
    else:
        print('  No hay relaciones usuario-hábito')
    
    print()
    print('=== USER_PROGRESS ===')
    cursor.execute('SELECT * FROM user_progress')
    progs = cursor.fetchall()
    if progs:
        for p in progs:
            print(f'  {p}')
    else:
        print('  No hay progresos')
    
    conn.close()
else:
    print('La base de datos NO existe')
