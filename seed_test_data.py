"""
Script para poblar datos de prueba del usuario test@test.com
Agrega:
  - HabitLogs de los ultimos 7 dias (para grafica de cumplimiento)
  - CoinTransactions de los ultimos 7 dias (para grafica de monedas)
  - Transactions de ahorro de los ultimos 30 dias (para grafica de capital)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from models import db, User, Habit, UserHabit, HabitLog, CoinTransaction, Category, Transaction
from datetime import date, timedelta, datetime

with app.app_context():
    user = User.query.filter_by(email='test@test.com').first()
    if not user:
        print("ERROR: Usuario test@test.com no encontrado. Ejecuta test_savings.py primero.")
        sys.exit(1)

    user_id = user.id
    today = date.today()

    # ─── 1. HabitLogs para grafica de cumplimiento (ultimos 7 dias) ───
    user_habits = UserHabit.query.filter_by(user_id=user_id).all()
    if not user_habits:
        print("El usuario no tiene habitos asignados. Se asignaran ahora.")
        habits = Habit.query.all()
        for h in habits:
            uh = UserHabit(user_id=user_id, habit_id=h.id, custom_name=h.name, custom_description=h.description, coins=h.coins)
            db.session.add(uh)
        db.session.commit()
        user_habits = UserHabit.query.filter_by(user_id=user_id).all()

    habit_logs_count = 0
    for i in range(7):
        d = today - timedelta(days=i)
        for uh in user_habits:
            existing = HabitLog.query.filter_by(user_id=user_id, habit_id=uh.habit_id, date=d).first()
            if not existing:
                # Simular ~70% de cumplimiento (completar algunos, otros no)
                if (uh.id + i) % 3 != 0:  # ~66% completados
                    log = HabitLog(user_id=user_id, habit_id=uh.habit_id, date=d, completed=True)
                    db.session.add(log)
                    habit_logs_count += 1

    # ─── 2. CoinTransactions para grafica de monedas (ultimos 7 dias) ───
    coin_tx_count = 0
    for i in range(7):
        d = today - timedelta(days=i)
        import random
        # 1-3 transacciones por dia con cantidades variables
        for _ in range(random.randint(1, 3)):
            coins = random.choice([5, 8, 10, 15])
            tx = CoinTransaction(
                user_id=user_id,
                amount=coins,
                concept=f'Habito completado - {d.strftime("%d/%m")}',
                created_at=datetime.combine(d, datetime.min.time())
            )
            db.session.add(tx)
            coin_tx_count += 1

    # ─── 3. Transactions de ahorro para grafica de capital (ultimos 30 dias) ───
    # Obtener categorias
    income_cats = Category.query.filter_by(type='income').all()
    expense_cats = Category.query.filter_by(type='expense').all()

    tx_count = 0
    for i in range(30):
        d = today - timedelta(days=i)
        # Un ingreso cada ~5 dias
        if i % 5 == 0 and income_cats:
            cat = income_cats[i % len(income_cats)]
            amount = random.choice([500, 800, 1000, 1200, 1500])
            existing = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.category_id == cat.id,
                Transaction.date == d,
                Transaction.type == 'income'
            ).first()
            if not existing:
                tx = Transaction(
                    user_id=user_id,
                    category_id=cat.id,
                    amount=amount,
                    description=f'Ingreso - {cat.name}',
                    date=d,
                    type='income'
                )
                db.session.add(tx)
                tx_count += 1

        # Un gasto cada ~3 dias
        if i % 3 == 0 and expense_cats:
            cat = expense_cats[i % len(expense_cats)]
            amount = random.choice([50, 80, 100, 120, 150, 200])
            existing = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.category_id == cat.id,
                Transaction.date == d,
                Transaction.type == 'expense'
            ).first()
            if not existing:
                tx = Transaction(
                    user_id=user_id,
                    category_id=cat.id,
                    amount=amount,
                    description=f'Gasto - {cat.name}',
                    date=d,
                    type='expense'
                )
                db.session.add(tx)
                tx_count += 1

    db.session.commit()

    print("=== DATOS DE PRUEBA AGREGADOS ===")
    print(f"Usuario: {user.email}")
    print(f"HabitLogs creados: {habit_logs_count}")
    print(f"CoinTransactions creadas: {coin_tx_count}")
    print(f"Transactions de ahorro creadas: {tx_count}")
    print("Listo! Las graficas ahora deberian mostrar datos.")
