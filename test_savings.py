import urllib.request, http.cookiejar, urllib.parse, json, sys

BASE = 'http://127.0.0.1:5000'
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def check(ok, msg):
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {msg}")
    return ok

def post(path, data_dict):
    data = urllib.parse.urlencode(data_dict).encode()
    return opener.open(BASE + path, data)

def get(path):
    return opener.open(BASE + path)

print("=" * 50)
print("PRUEBA DEL MODULO DE AHORROS")
print("=" * 50)

# 1. Login
print("\n1. LOGIN")
r = post('/login', {'email': 'test@test.com', 'password': '123456'})
check(r.status == 200, f"Login: {r.status}")

# 2. Setup habits
print("\n2. SETUP HABITS")
r = post('/setup_habits', {'habits': ['1', '2', '3']})
check(r.status == 200, f"Setup habits: {r.status}")

# 3. Acceder a savings
print("\n3. ACCEDER A /savings")
r = get('/savings')
html = r.read().decode('utf-8', errors='replace')
check(r.status == 200, "HTTP 200")
check('Sistema de Ahorros' in html, "Titulo 'Sistema de Ahorros'")
check('Registrar Ingreso' in html, "Boton 'Registrar Ingreso'")
check('Registrar Gasto' in html, "Boton 'Registrar Gasto'")
check('Historial de Transacciones' in html, "Seccion 'Historial de Transacciones'")
check('Metas de Ahorro' in html, "Seccion 'Metas de Ahorro'")
check('Capital a trav' in html, "Grafica 'Capital a traves del tiempo'")
check('Gastos por Categor' in html, "Grafica 'Gastos por Categoria'")
check('balanceChart' in html, "Canvas balanceChart")
check('categoryPieChart' in html, "Canvas categoryPieChart")

# 4. Registrar transacciones
print("\n4. REGISTRAR TRANSACCIONES")

# Ingreso: Salario (cat 1)
r = post('/savings/add_transaction', {
    'type': 'income', 'amount': '2500.00', 'category_id': '1',
    'description': 'Salario mensual', 'date': '2026-05-01'
})
check(r.status == 200, "Ingreso Salario $2500")

# Gasto: Alimentacion (cat 6)
r = post('/savings/add_transaction', {
    'type': 'expense', 'amount': '150.00', 'category_id': '6',
    'description': 'Supermercado', 'date': '2026-05-02'
})
check(r.status == 200, "Gasto Alimentacion $150")

# Gasto: Transporte (cat 7)
r = post('/savings/add_transaction', {
    'type': 'expense', 'amount': '45.00', 'category_id': '7',
    'description': 'Gasolina', 'date': '2026-05-03'
})
check(r.status == 200, "Gasto Transporte $45")

# Ingreso: Freelance (cat 2)
r = post('/savings/add_transaction', {
    'type': 'income', 'amount': '500.00', 'category_id': '2',
    'description': 'Proyecto freelance', 'date': '2026-05-05'
})
check(r.status == 200, "Ingreso Freelance $500")

# Gasto: Entretenimiento (cat 11)
r = post('/savings/add_transaction', {
    'type': 'expense', 'amount': '30.00', 'category_id': '11',
    'description': 'Netflix', 'date': '2026-05-06'
})
check(r.status == 200, "Gasto Entretenimiento $30")

# 5. Verificar APIs
print("\n5. VERIFICAR APIs")

r = get('/api/savings/balance_history?days=30')
data = json.loads(r.read())
check(len(data['labels']) > 0, f"Balance history: {len(data['labels'])} dias")
check(data['data'][-1] == 2775.0, f"Balance final = $2775 (2500+500-150-45-30) -> {data['data'][-1]}")

r = get('/api/savings/category_pie')
data = json.loads(r.read())
check(len(data['labels']) > 0, f"Category pie: {len(data['labels'])} categorias")
check('Alimentacion' in str(data['labels']) or 'Alimentaci' in str(data['labels']), "Categoria Alimentacion presente")

r = get('/api/savings/goals_progress')
data = json.loads(r.read())
check(len(data['goals']) == 0, "Goals: 0 (aun no creamos)")

# 6. Crear meta de ahorro
print("\n6. CREAR META DE AHORRO")
r = post('/savings/add_goal', {
    'name': 'Viaje a la playa', 'target_amount': '3000.00',
    'current_amount': '500.00', 'deadline': '2026-12-31', 'color': '#1cc88a'
})
check(r.status == 200, "Meta 'Viaje a la playa' creada")

r = get('/api/savings/goals_progress')
data = json.loads(r.read())
check(len(data['goals']) == 1, f"Goals: {len(data['goals'])}")
check(data['goals'][0]['name'] == 'Viaje a la playa', f"Nombre: {data['goals'][0]['name']}")
check(data['goals'][0]['percentage'] == 16, f"Progreso: {data['goals'][0]['percentage']}% (500/3000=16%)")

# 7. Verificar dashboard con datos
print("\n7. VERIFICAR DASHBOARD CON DATOS")
r = get('/savings')
html = r.read().decode('utf-8', errors='replace')
check('Salario mensual' in html, "Transaccion 'Salario mensual' visible")
check('Supermercado' in html, "Transaccion 'Supermercado' visible")
check('Gasolina' in html, "Transaccion 'Gasolina' visible")
check('Proyecto freelance' in html, "Transaccion 'Proyecto freelance' visible")
check('Netflix' in html, "Transaccion 'Netflix' visible")
check('Viaje a la playa' in html, "Meta 'Viaje a la playa' visible")

print("\n" + "=" * 50)
print("PRUEBAS COMPLETADAS")
print("=" * 50)
