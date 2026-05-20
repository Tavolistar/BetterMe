from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import date, timedelta, datetime
from functools import wraps
import os
import sys
import logging
import secrets
from dotenv import load_dotenv
from flask_mail import Mail, Message

from models import db, User, Task, Habit, UserHabit, UserProgress, HabitLog, ShopItem, CoinTransaction, UserPurchase, Category, Transaction, SavingsGoal

# Cargar variables de entorno
load_dotenv()

# Configurar logging para Render (stdout visible en logs)
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    stream=sys.stdout
)
log = logging.getLogger(__name__)

# Obtener la ruta base del proyecto
basedir = os.path.abspath(os.path.dirname(__file__))

# En Render, la DB viene de DATABASE_URL (PostgreSQL).
# En local, usa SQLite.
is_production = os.getenv('RENDER', '') == 'true'

if is_production:
    app = Flask(__name__)
    # Render provee DATABASE_URL automáticamente si agregas PostgreSQL
    database_url = os.getenv('DATABASE_URL', '')
    # SQLAlchemy 2.x requiere postgresql:// pero Render da postgres://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app = Flask(__name__, instance_path=os.path.join(basedir, 'instance'))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///betterme.db')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', '')

# Inicializar extensiones
db.init_app(app)
mail = Mail(app)


# ─── Filtro Jinja para resolver ruta de avatares ────────────────────
@app.template_filter('avatar_url')
def avatar_url_filter(filename):
    """Resuelve la ruta correcta para avatares.
    Los avatares predeterminados (undraw_*.svg) están en static/img/.
    Los avatares seleccionables (avatar_*.svg) están en static/avatars/.
    """
    if filename and filename.startswith('avatar_'):
        return url_for('static', filename='avatars/' + filename)
    return url_for('static', filename='img/' + (filename or 'undraw_profile.svg'))


# ─── Decorador: login requerido ─────────────────────────────────────

def login_required(f):
    """Decorador que redirige al login si el usuario no está autenticado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ─── Crear tablas y datos iniciales ──────────────────────────────────

with app.app_context():
    db.create_all()

    # Crear hábitos predefinidos si no existen
    if Habit.query.count() == 0:
        default_habits = [
            Habit(name='Beber agua', description='Tomar al menos 8 vasos de agua al día', coins=5),
            Habit(name='Ejercicio 30 min', description='Realizar actividad física por 30 minutos', coins=10),
            Habit(name='Leer 20 páginas', description='Leer 20 páginas de un libro', coins=8)
        ]
        db.session.bulk_save_objects(default_habits)
        db.session.commit()

    # Crear categorías globales de ahorro si no existen
    if Category.query.count() == 0:
        default_categories = [
            # Ingresos
            Category(name='Salario', icon='fas fa-briefcase', color='#1cc88a', type='income'),
            Category(name='Freelance', icon='fas fa-laptop-code', color='#36b9cc', type='income'),
            Category(name='Inversiones', icon='fas fa-chart-line', color='#4e73df', type='income'),
            Category(name='Ventas', icon='fas fa-tag', color='#f6c23e', type='income'),
            Category(name='Otros ingresos', icon='fas fa-plus-circle', color='#858796', type='income'),
            # Gastos
            Category(name='Alimentación', icon='fas fa-utensils', color='#e74a3b', type='expense'),
            Category(name='Transporte', icon='fas fa-bus', color='#fd7e14', type='expense'),
            Category(name='Vivienda', icon='fas fa-home', color='#5a5c69', type='expense'),
            Category(name='Servicios', icon='fas fa-bolt', color='#f6c23e', type='expense'),
            Category(name='Salud', icon='fas fa-heartbeat', color='#e74a3b', type='expense'),
            Category(name='Entretenimiento', icon='fas fa-film', color='#36b9cc', type='expense'),
            Category(name='Educación', icon='fas fa-book', color='#4e73df', type='expense'),
            Category(name='Ropa', icon='fas fa-tshirt', color='#1cc88a', type='expense'),
            Category(name='Ahorro', icon='fas fa-piggy-bank', color='#1cc88a', type='expense'),
            Category(name='Otros gastos', icon='fas fa-ellipsis-h', color='#858796', type='expense'),
        ]
        db.session.bulk_save_objects(default_categories)
        db.session.commit()

    # ─── Seed: usuario de prueba y datos demo ──────────────────────────
    if is_production:
        from werkzeug.security import generate_password_hash
        log.info("Modo produccion detectado. Iniciando seed de datos...")
        try:
            # Verificar conexion a DB
            db.session.execute(db.text('SELECT 1'))
            log.info("Conexion a PostgreSQL OK")
        except Exception as e:
            log.error(f"ERROR CRITICO: No se pudo conectar a la DB: {e}")

        if User.query.filter_by(email='test@test.com').first() is None:
            try:
                log.info("Usuario test no existe. Creando...")
                # Crear usuario test
                test_user = User(
                    email='test@test.com',
                    password_hash=generate_password_hash('test123'),
                    name='TestUser',
                    avatar='avatar_1.svg',
                    created_at=datetime.now() - timedelta(days=60)
                )
                db.session.add(test_user)
                db.session.commit()
                log.info(f"Usuario test creado: id={test_user.id}")

                # Crear progreso inicial con monedas
                progress = UserProgress(user_id=test_user.id, coins=500)
                db.session.add(progress)
                db.session.commit()
                log.info("UserProgress creado: coins=500")

                # Asignar habitos al usuario de prueba
                all_habits = Habit.query.all()
                log.info(f"Asignando {len(all_habits)} habitos...")
                for h in all_habits:
                    uh = UserHabit(user_id=test_user.id, habit_id=h.id)
                    db.session.add(uh)
                db.session.commit()

                # HabitLogs ultimos 14 dias
                log_count = 0
                for i in range(14):
                    d = date.today() - timedelta(days=i)
                    for h in all_habits:
                        if (i + h.id) % 2 == 0:
                            log_obj = HabitLog(
                                user_id=test_user.id,
                                habit_id=h.id,
                                date=d,
                                completed=True
                            )
                            db.session.add(log_obj)
                            log_count += 1
                db.session.commit()
                log.info(f"HabitLogs creados: {log_count}")

                # CoinTransactions
                for i in range(20):
                    ct = CoinTransaction(
                        user_id=test_user.id,
                        amount=10,
                        concept=f'Habito completado - Dia {i+1}',
                        created_at=datetime.now() - timedelta(days=i)
                    )
                    db.session.add(ct)
                db.session.commit()
                log.info("CoinTransactions creadas: 20")

                # Transacciones de ahorro
                income_cats = Category.query.filter_by(type='income').all()
                expense_cats = Category.query.filter_by(type='expense').all()
                if income_cats and expense_cats:
                    for i in range(15):
                        d = date.today() - timedelta(days=i*2)
                        tx = Transaction(
                            user_id=test_user.id,
                            category_id=income_cats[i % len(income_cats)].id,
                            amount=5000 + (i * 200),
                            description=f'Ingreso {i+1}',
                            date=d,
                            type='income'
                        )
                        db.session.add(tx)
                    for i in range(20):
                        d = date.today() - timedelta(days=i*2 + 1)
                        tx = Transaction(
                            user_id=test_user.id,
                            category_id=expense_cats[i % len(expense_cats)].id,
                            amount=500 + (i * 50),
                            description=f'Gasto {i+1}',
                            date=d,
                            type='expense'
                        )
                        db.session.add(tx)
                    db.session.commit()
                    log.info("Transactions de ahorro creadas")
                else:
                    log.warning(f"No hay categorias. income_cats={len(income_cats)} expense_cats={len(expense_cats)}")

                # Metas de ahorro
                goals = [
                    SavingsGoal(user_id=test_user.id, name='Viaje a la playa', target_amount=50000, current_amount=15000, deadline=date.today() + timedelta(days=90), color='#4e73df'),
                    SavingsGoal(user_id=test_user.id, name='Fondo de emergencia', target_amount=30000, current_amount=30000, deadline=date.today() + timedelta(days=30), color='#1cc88a', completed=True),
                    SavingsGoal(user_id=test_user.id, name='Curso online', target_amount=10000, current_amount=3500, deadline=date.today() + timedelta(days=45), color='#f6c23e'),
                ]
                db.session.bulk_save_objects(goals)
                db.session.commit()
                log.info("SavingsGoals creadas: 3")

                log.info("*** SEED COMPLETADO: test@test.com / test123 ***")
            except Exception as e:
                db.session.rollback()
                log.error(f"ERROR EN SEED: {type(e).__name__}: {e}")
                import traceback
                log.error(traceback.format_exc())
        else:
            log.info("Usuario test ya existe, omitiendo seed.")


# ─── Función auxiliar ───────────────────────────────────────────────

def get_user_habits(user_id):
    """Obtiene los hábitos del usuario con su progreso individual.
    Solo devuelve los hábitos que el usuario seleccionó durante el registro
    (los que tienen un registro UserHabit existente)."""
    user_habits_records = UserHabit.query.filter_by(user_id=user_id).all()
    user_habits = []

    for uh in user_habits_records:
        habit = Habit.query.get(uh.habit_id)
        if habit:
            user_habits.append({
                'habit': habit,
                'user_habit': uh
            })

    return user_habits


# ─── Rutas de Autenticación ─────────────────────────────────────────

@app.route("/register", methods=['GET', 'POST'])
def register():
    """Registro de nuevo usuario."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validaciones
        if not name or not email or not password:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template("register.html")

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template("register.html")

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template("register.html")

        # Verificar si el email ya está registrado
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Ya existe una cuenta con este correo electrónico.', 'danger')
            return render_template("register.html")

        # Crear usuario
        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Para obtener el ID del usuario

        # Crear progreso inicial para el usuario
        progress = UserProgress(user_id=user.id, coins=100, streak=0)
        db.session.add(progress)

        db.session.commit()

        # Iniciar sesión automáticamente
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        session['user_avatar'] = user.avatar

        flash('¡Bienvenido a BetterMe! Ahora configura tus hábitos diarios.', 'success')
        return redirect(url_for('setup_habits'))

    return render_template("register.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    """Inicio de sesión."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        if not email or not password:
            flash('Por favor, ingresa tu correo y contraseña.', 'danger')
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            flash('Correo electrónico o contraseña incorrectos.', 'danger')
            return render_template("login.html")

        # Iniciar sesión
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        session['user_avatar'] = user.avatar
        session.permanent = remember

        flash(f'¡Bienvenido de nuevo, {user.name}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Cierre de sesión."""
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('index'))


# ─── Recuperación de Contraseña ─────────────────────────────────────

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_password():
    """Solicitar restablecimiento de contraseña."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Por favor, ingresa tu correo electrónico.', 'danger')
            return render_template("reset_password.html")

        user = User.query.filter_by(email=email).first()

        if user:
            token = secrets.token_urlsafe(32)
            session['reset_token'] = token
            session['reset_email'] = email

            reset_url = url_for('reset_password_confirm', token=token, _external=True)

            try:
                msg = Message(
                    subject='BetterMe - Restablecer tu contraseña',
                    recipients=[email],
                    body=f"""Hola {user.name},

Has solicitado restablecer tu contraseña de BetterMe.

Haz clic en el siguiente enlace para crear una nueva contraseña:
{reset_url}

Si no solicitaste este cambio, ignora este mensaje.

¡Gracias por usar BetterMe!
"""
                )
                mail.send(msg)
                flash('Te hemos enviado un enlace de recuperación a tu correo electrónico.', 'info')
            except Exception:
                flash(f'[Modo desarrollo] Enlace de recuperación: {reset_url}', 'info')
        else:
            flash('Si el correo está registrado, recibirás un enlace de recuperación.', 'info')

        return redirect(url_for('login'))

    return render_template("reset_password.html")


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_password_confirm(token):
    """Confirmar restablecimiento de contraseña."""
    stored_token = session.get('reset_token')
    stored_email = session.get('reset_email')

    if not stored_token or stored_token != token or not stored_email:
        flash('El enlace de recuperación no es válido o ha expirado.', 'danger')
        return redirect(url_for('reset_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not password:
            flash('La contraseña es obligatoria.', 'danger')
            return render_template("reset_password_confirm.html", token=token)

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template("reset_password_confirm.html", token=token)

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template("reset_password_confirm.html", token=token)

        user = User.query.filter_by(email=stored_email).first()
        if user:
            user.set_password(password)
            db.session.commit()
            session.pop('reset_token', None)
            session.pop('reset_email', None)
            flash('Tu contraseña ha sido actualizada exitosamente. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Ha ocurrido un error. Por favor, solicita un nuevo enlace.', 'danger')
            return redirect(url_for('reset_password'))

    return render_template("reset_password_confirm.html", token=token)


# ─── Rutas públicas ─────────────────────────────────────────────────

@app.route("/")
def index():
    """Página de inicio / landing page."""
    return render_template("index.html")


@app.route("/premium")
@login_required
def premium():
    """Página de planes y precios Premium."""
    return render_template("premium.html")


@app.route("/avatars")
@login_required
def avatars():
    """AV-02: Galería de avatares. Muestra los disponibles y los bloqueados."""
    user_id = session['user_id']
    user = User.query.get(user_id)
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    # Lista de avatares disponibles (SVG reales)
    avatar_list = [
        {'id': 1, 'file': 'avatar_1.svg', 'name': 'Carlos', 'gender': 'M', 'description': 'Ejecutivo moderno', 'price': 0},
        {'id': 2, 'file': 'avatar_2.svg', 'name': 'Valentina', 'gender': 'F', 'description': 'Chica con estilo', 'price': 0},
        {'id': 3, 'file': 'avatar_3.svg', 'name': 'Marcus', 'gender': 'M', 'description': 'Deportista urbano', 'price': 0},
        {'id': 4, 'file': 'avatar_4.svg', 'name': 'Sofía', 'gender': 'F', 'description': 'Chica golden', 'price': 0},
        {'id': 5, 'file': 'avatar_5.svg', 'name': 'Don Alberto', 'gender': 'M', 'description': 'Caballero formal', 'price': 0},
        {'id': 6, 'file': 'avatar_6.svg', 'name': 'Lucía', 'gender': 'F', 'description': 'Chica deportista', 'price': 0},
        {'id': 7, 'file': 'avatar_7.svg', 'name': 'Camila', 'gender': 'F', 'description': 'Chica pelirroja', 'price': 0},
        {'id': 8, 'file': 'avatar_8.svg', 'name': 'Mateo', 'gender': 'M', 'description': 'Joven con gorra', 'price': 0},
    ]

    # Avatars de la tienda (desbloqueables con monedas)
    shop_avatars = ShopItem.query.filter_by(category='avatar').all()
    purchased_ids = set()
    if user_id:
        purchases = UserPurchase.query.filter_by(user_id=user_id).all()
        purchased_ids = {p.item_id for p in purchases}

    # Avatar actual del usuario
    current_avatar = user.avatar if user else 'undraw_profile.svg'

    return render_template("avatars.html",
                           avatars=avatar_list,
                           shop_avatars=shop_avatars,
                           purchased_ids=purchased_ids,
                           current_avatar=current_avatar,
                           coins=progress.coins if progress else 0)


@app.route("/select_avatar/<path:avatar_file>")
@login_required
def select_avatar(avatar_file):
    """AV-02: Cambiar el avatar del usuario."""
    user_id = session['user_id']
    user = User.query.get(user_id)

    # Validar que el archivo existe en static/avatars/
    import os
    avatar_path = os.path.join(app.root_path, 'static', 'avatars', avatar_file)
    if not os.path.exists(avatar_path):
        flash('El avatar no existe.', 'danger')
        return redirect(url_for('avatars'))

    user.avatar = avatar_file
    db.session.commit()

    # Actualizar sesión
    session['user_avatar'] = avatar_file

    flash(f'✅ ¡Avatar actualizado!', 'success')
    return redirect(url_for('dashboard'))


# ─── Onboarding: Configuración inicial de hábitos ────────────────────

@app.route("/setup_habits", methods=['GET', 'POST'])
@login_required
def setup_habits():
    """Pantalla de configuración de hábitos diarios.
    Se muestra al registrarse o cuando el usuario quiere modificar sus hábitos."""
    user_id = session['user_id']
    available_habits = Habit.query.filter_by(is_custom=False).all()

    if request.method == 'POST':
        # Obtener hábitos predefinidos seleccionados
        selected_habit_ids = request.form.getlist('habits')
        selected_habit_ids = [int(hid) for hid in selected_habit_ids if hid.isdigit()]

        # Obtener hábitos personalizados escritos por el usuario
        custom_names = request.form.getlist('custom_habit_name')
        custom_descriptions = request.form.getlist('custom_habit_desc')
        custom_coins_list = request.form.getlist('custom_habit_coins')

        # Validar que haya al menos un hábito (predefinido o personalizado)
        if not selected_habit_ids and not any(n.strip() for n in custom_names):
            flash('Debes seleccionar o crear al menos un hábito diario.', 'danger')
            return render_template("setup_habits.html", habits=available_habits)

        # Eliminar todos los UserHabit actuales del usuario (para reemplazar)
        UserHabit.query.filter_by(user_id=user_id).delete()

        # Crear UserHabit para los hábitos predefinidos seleccionados
        for habit_id in selected_habit_ids:
            uh = UserHabit(user_id=user_id, habit_id=habit_id, completed=False)
            db.session.add(uh)

        # Crear hábitos personalizados
        for i, name in enumerate(custom_names):
            name = name.strip()
            if not name:
                continue
            desc = custom_descriptions[i].strip() if i < len(custom_descriptions) else ''
            coins_val = int(custom_coins_list[i]) if i < len(custom_coins_list) and custom_coins_list[i].isdigit() else 5

            new_habit = Habit(
                name=name,
                description=desc,
                coins=coins_val,
                is_custom=True,
                user_id=user_id
            )
            db.session.add(new_habit)
            db.session.flush()

            uh = UserHabit(user_id=user_id, habit_id=new_habit.id, completed=False)
            db.session.add(uh)

        db.session.commit()
        flash('¡Tus hábitos diarios han sido configurados!', 'success')
        return redirect(url_for('dashboard'))

    # GET: mostrar los hábitos actuales del usuario (si ya tiene)
    user_habits_data = get_user_habits(user_id)
    selected_ids = [uh['habit'].id for uh in user_habits_data if not uh['habit'].is_custom]
    custom_habits = [uh['habit'] for uh in user_habits_data if uh['habit'].is_custom]

    return render_template("setup_habits.html",
                           habits=available_habits,
                           selected_ids=selected_ids,
                           custom_habits=custom_habits)


# ─── Rutas del Dashboard (protegidas) ───────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard principal con tareas, hábitos y progreso."""
    user_id = session['user_id']

    # Si el usuario no tiene hábitos configurados, redirigir al onboarding
    user_habits_data = get_user_habits(user_id)
    if not user_habits_data:
        flash('Configura tus hábitos diarios para comenzar.', 'info')
        return redirect(url_for('setup_habits'))

    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.created_at.desc()).all()
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    # RA-02: Verificar si se saltó un día al cargar dashboard
    if progress:
        today = date.today()
        yesterday = date.fromordinal(today.toordinal() - 1)
        if progress.last_activity and progress.last_activity < yesterday:
            progress.reset_streak()
            db.session.commit()

    # Calcular estadísticas basadas en UserHabit
    total_habits = len(user_habits_data)
    completed_habits = sum(1 for uh in user_habits_data if uh['user_habit'].completed)
    progress_percentage = int((completed_habits / total_habits * 100)) if total_habits > 0 else 0

    return render_template("dashboard.html",
                           tasks=tasks,
                           user_habits_data=user_habits_data,
                           coins=progress.coins if progress else 100,
                           streak=progress.streak if progress else 0,
                           best_streak=progress.best_streak if progress else 0,
                           progress_percentage=progress_percentage,
                           completed_habits=completed_habits,
                           total_habits=total_habits)


@app.route("/add_task", methods=['POST'])
@login_required
def add_task():
    task_text = request.form.get('task_text')
    if task_text:
        new_task = Task(text=task_text, user_id=session['user_id'])
        db.session.add(new_task)
        db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/delete_task/<int:task_id>")
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/toggle_task/<int:task_id>")
@login_required
def toggle_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    task.completed = not task.completed

    progress = UserProgress.query.filter_by(user_id=session['user_id']).first()
    if progress:
        progress.update_streak()
        if task.completed:
            progress.coins += 10
        else:
            progress.coins = max(0, progress.coins - 5)
        db.session.commit()

    return redirect(url_for('dashboard'))




@app.route("/reset_day")
@login_required
def reset_day():
    user_id = session['user_id']

    # Resetear solo los hábitos del usuario actual
    user_habits = UserHabit.query.filter_by(user_id=user_id).all()
    for uh in user_habits:
        uh.completed = False
        uh.completed_date = None

    progress = UserProgress.query.filter_by(user_id=user_id).first()
    if progress:
        progress.update_streak()

    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/add_sample_tasks")
@login_required
def add_sample_tasks():
    user_id = session['user_id']
    sample_tasks = [
        "Meditar 10 minutos",
        "Escribir en el diario",
        "Planificar el día siguiente",
        "Aprender algo nuevo"
    ]

    for task_text in sample_tasks:
        if not Task.query.filter_by(text=task_text, user_id=user_id).first():
            new_task = Task(text=task_text, user_id=user_id)
            db.session.add(new_task)

    db.session.commit()
    return redirect(url_for('dashboard'))


# ─── CRUD de Hábitos ────────────────────────────────────────────────

@app.route("/create_habit", methods=['POST'])
@login_required
def create_habit():
    """HA-01: Crear un hábito personalizado desde el dashboard."""
    user_id = session['user_id']
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    coins = request.form.get('coins', 5, type=int)

    if not name:
        flash('El nombre del hábito es obligatorio.', 'danger')
        return redirect(url_for('dashboard'))

    # Crear el hábito
    new_habit = Habit(
        name=name,
        description=description,
        coins=max(1, min(coins, 100)),
        is_custom=True,
        user_id=user_id
    )
    db.session.add(new_habit)
    db.session.flush()

    # Asignarlo al usuario
    uh = UserHabit(user_id=user_id, habit_id=new_habit.id, completed=False)
    db.session.add(uh)
    db.session.commit()

    flash(f'✅ Hábito "{name}" creado correctamente.', 'success')
    return redirect(url_for('dashboard'))


@app.route("/edit_habit/<int:habit_id>", methods=['POST'])
@login_required
def edit_habit(habit_id):
    """HA-02: Editar un hábito existente."""
    user_id = session['user_id']
    habit = Habit.query.get_or_404(habit_id)

    # Solo el dueño puede editar hábitos personalizados
    if not habit.is_custom or habit.user_id != user_id:
        flash('No puedes editar este hábito.', 'danger')
        return redirect(url_for('dashboard'))

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    coins = request.form.get('coins', 5, type=int)

    if not name:
        flash('El nombre del hábito es obligatorio.', 'danger')
        return redirect(url_for('dashboard'))

    habit.name = name
    habit.description = description
    habit.coins = max(1, min(coins, 100))
    db.session.commit()

    flash(f'✅ Hábito "{name}" actualizado.', 'success')
    return redirect(url_for('dashboard'))


@app.route("/delete_habit/<int:habit_id>", methods=['POST'])
@login_required
def delete_habit(habit_id):
    """HA-03: Eliminar un hábito."""
    user_id = session['user_id']
    habit = Habit.query.get_or_404(habit_id)

    # Solo el dueño puede eliminar hábitos personalizados
    if not habit.is_custom or habit.user_id != user_id:
        flash('No puedes eliminar este hábito.', 'danger')
        return redirect(url_for('dashboard'))

    name = habit.name

    # Eliminar relaciones
    UserHabit.query.filter_by(user_id=user_id, habit_id=habit_id).delete()
    HabitLog.query.filter_by(user_id=user_id, habit_id=habit_id).delete()
    db.session.delete(habit)
    db.session.commit()

    flash(f'🗑️ Hábito "{name}" eliminado.', 'success')
    return redirect(url_for('dashboard'))


# ─── API para gráfica de cumplimiento ──────────────────────────────

@app.route("/api/habit_stats")
@login_required
def api_habit_stats():
    """Devuelve datos JSON para la gráfica de cumplimiento (últimos 7 días)."""
    user_id = session['user_id']
    days = request.args.get('days', 7, type=int)
    days = max(7, min(days, 30))

    today = date.today()
    dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

    # Obtener hábitos del usuario
    user_habits_data = get_user_habits(user_id)
    total_habits = len(user_habits_data)

    labels = []
    data = []

    for d in dates:
        label = d.strftime('%d/%m')
        labels.append(label)

        if total_habits == 0:
            data.append(0)
        else:
            # Contar cuántos hábitos se completaron en esa fecha
            completed = HabitLog.query.filter_by(
                user_id=user_id, date=d, completed=True
            ).count()
            percentage = int((completed / total_habits) * 100)
            data.append(percentage)

    return jsonify({
        'labels': labels,
        'data': data,
        'total_habits': total_habits
    })


@app.route("/api/coin_stats")
@login_required
def api_coin_stats():
    """Devuelve datos JSON para la gráfica de monedas a través del tiempo (últimos 14 días)."""
    user_id = session['user_id']
    days = request.args.get('days', 14, type=int)
    days = max(7, min(days, 30))

    today = date.today()
    dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

    labels = []
    data = []
    balance = 100  # saldo inicial

    for d in dates:
        label = d.strftime('%d/%m')
        labels.append(label)

        # Sumar transacciones de ese día
        day_transactions = CoinTransaction.query.filter(
            CoinTransaction.user_id == user_id,
            db.func.date(CoinTransaction.created_at) == d
        ).all()

        for tx in day_transactions:
            balance += tx.amount

        data.append(balance)

    return jsonify({
        'labels': labels,
        'data': data
    })


@app.route("/api/check_streak")
@login_required
def api_check_streak():
    """RA-02: Verifica si el usuario se saltó un día y resetea la racha si es necesario.
    Se llama al cargar el dashboard."""
    user_id = session['user_id']
    progress = UserProgress.query.filter_by(user_id=user_id).first()
    if not progress:
        return jsonify({'streak': 0, 'best_streak': 0})

    today = date.today()
    yesterday = date.fromordinal(today.toordinal() - 1)

    # Si last_activity es anterior a ayer, significa que se saltó al menos un día
    if progress.last_activity and progress.last_activity < yesterday:
        progress.reset_streak()
        db.session.commit()

    return jsonify({
        'streak': progress.streak,
        'best_streak': progress.best_streak
    })


@app.route("/api/streak_calendar")
@login_required
def api_streak_calendar():
    """RA-05: Devuelve datos para el calendario visual de rachas (últimos 60 días).
    Cada día indica si el usuario completó AL MENOS 1 hábito."""
    user_id = session['user_id']
    days = request.args.get('days', 60, type=int)
    days = max(30, min(days, 90))

    today = date.today()
    start_date = date.fromordinal(today.toordinal() - days + 1)

    # Obtener todos los HabitLog del usuario en el rango
    logs = HabitLog.query.filter(
        HabitLog.user_id == user_id,
        HabitLog.date >= start_date,
        HabitLog.date <= today,
        HabitLog.completed == True
    ).all()

    # Crear un set de días donde completó AL MENOS 1 hábito
    completed_days = set()
    for log in logs:
        completed_days.add(log.date.isoformat())

    # Generar array día por día
    calendar_data = []
    for i in range(days):
        d = date.fromordinal(start_date.toordinal() + i)
        date_str = d.isoformat()
        calendar_data.append({
            'date': date_str,
            'completed': date_str in completed_days,
            'day_name': d.strftime('%a'),
            'day_of_week': d.weekday(),  # 0=lunes, 6=domingo
            'is_today': d == today
        })

    return jsonify({
        'calendar': calendar_data,
        'start_date': start_date.isoformat(),
        'end_date': today.isoformat(),
        'total_days': days,
        'completed_days': len(completed_days)
    })


@app.route("/toggle_habit/<int:habit_id>")
@login_required
def toggle_habit(habit_id):
    """MO-02/MO-03: Marcar/desmarcar hábito. +10 al completar, -5 al desmarcar.
    RA-01/RA-02: Actualiza racha solo al COMPLETAR un hábito (no al desmarcar)."""
    user_id = session['user_id']

    # Buscar o crear el UserHabit para este usuario y hábito
    uh = UserHabit.query.filter_by(user_id=user_id, habit_id=habit_id).first()
    if uh is None:
        uh = UserHabit(user_id=user_id, habit_id=habit_id, completed=False)
        db.session.add(uh)
        db.session.flush()

    # Guardar estado anterior para saber si completó o desmarcó
    was_completed = uh.completed
    uh.completed = not uh.completed
    uh.completed_date = date.today() if uh.completed else None

    habit = Habit.query.get_or_404(habit_id)
    progress = UserProgress.query.filter_by(user_id=user_id).first()
    if progress:
        if uh.completed and not was_completed:
            # RA-01: Solo actualizar racha cuando COMPLETA un hábito
            progress.update_streak()
            # MO-02: +10 monedas por completar hábito
            progress.coins += 10
            # Registrar transacción positiva
            tx = CoinTransaction(
                user_id=user_id,
                amount=10,
                concept=f"✅ Hábito completado: {habit.name}"
            )
            db.session.add(tx)
        elif not uh.completed and was_completed:
            # MO-03: -5 monedas por desmarcar hábito (NO afecta la racha)
            progress.coins = max(0, progress.coins - 5)
            # Registrar transacción negativa
            tx = CoinTransaction(
                user_id=user_id,
                amount=-5,
                concept=f"❌ Hábito desmarcado: {habit.name}"
            )
            db.session.add(tx)

    # Registrar en HabitLog para el histórico
    today = date.today()
    log = HabitLog.query.filter_by(
        user_id=user_id, habit_id=habit_id, date=today
    ).first()

    if log:
        log.completed = uh.completed
    else:
        log = HabitLog(
            user_id=user_id,
            habit_id=habit_id,
            date=today,
            completed=uh.completed
        )
        db.session.add(log)

    db.session.commit()
    return redirect(url_for('dashboard'))


# ====== MO-05: HISTORIAL DE TRANSACCIONES ======
@app.route("/coin_history")
@login_required
def coin_history():
    """Muestra el historial de transacciones de monedas del usuario."""
    user_id = session['user_id']
    transactions = CoinTransaction.query.filter_by(user_id=user_id)\
        .order_by(CoinTransaction.created_at.desc()).all()
    progress = UserProgress.query.filter_by(user_id=user_id).first()
    return render_template("coin_history.html",
                           transactions=transactions,
                           coins=progress.coins if progress else 0)


# ====== MO-06: TIENDA ======
@app.route("/shop")
@login_required
def shop():
    """Tienda de BetterMe: compra avatares y productos con monedas."""
    user_id = session['user_id']
    progress = UserProgress.query.filter_by(user_id=user_id).first()
    items = ShopItem.query.all()
    # IDs de items que el usuario ya compró
    purchased_ids = [p.item_id for p in UserPurchase.query.filter_by(user_id=user_id).all()]
    return render_template("shop.html",
                           items=items,
                           coins=progress.coins if progress else 0,
                           purchased_ids=purchased_ids)


@app.route("/buy_item/<int:item_id>")
@login_required
def buy_item(item_id):
    """Comprar un item de la tienda con monedas."""
    user_id = session['user_id']
    item = ShopItem.query.get_or_404(item_id)
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    if not progress:
        flash('Error al obtener tu progreso.', 'danger')
        return redirect(url_for('shop'))

    # Verificar si ya lo compró
    existing = UserPurchase.query.filter_by(user_id=user_id, item_id=item_id).first()
    if existing:
        flash('Ya tienes este producto.', 'warning')
        return redirect(url_for('shop'))

    # Verificar si tiene suficientes monedas
    if progress.coins < item.price:
        flash(f'No tienes suficientes monedas. Necesitas {item.price} 🪙 y tienes {progress.coins}.', 'danger')
        return redirect(url_for('shop'))

    # Descontar monedas
    progress.coins -= item.price

    # Registrar compra
    purchase = UserPurchase(user_id=user_id, item_id=item_id)
    db.session.add(purchase)

    # Registrar transacción
    tx = CoinTransaction(
        user_id=user_id,
        amount=-item.price,
        concept=f"🛒 Compra: {item.name}"
    )
    db.session.add(tx)

    # Si es un avatar, actualizar el avatar del usuario
    if item.category == 'avatar' and item.image:
        user = User.query.get(user_id)
        if user:
            user.avatar = item.image

    db.session.commit()
    flash(f'🎉 ¡Has comprado {item.name} por {item.price} monedas!', 'success')
    return redirect(url_for('shop'))


# ====== SEMILLA DE PRODUCTOS PARA LA TIENDA ======
@app.route("/seed_shop")
def seed_shop():
    """Poblar la tienda con productos iniciales (reemplaza productos existentes)."""
    # Eliminar productos existentes y sus compras asociadas (para re-poblar)
    UserPurchase.query.delete()
    ShopItem.query.delete()
    db.session.commit()

    products = [
        # AV-03: Avatares desbloqueables con monedas (SVGs reales)
        ShopItem(name="Avatar Ejecutivo", description="Carlos - Estilo ejecutivo moderno.", price=50, category="avatar", image="avatar_1.svg"),
        ShopItem(name="Avatar Valentina", description="Valentina - Chica con estilo.", price=50, category="avatar", image="avatar_2.svg"),
        ShopItem(name="Avatar Marcus", description="Marcus - Deportista urbano.", price=50, category="avatar", image="avatar_3.svg"),
        ShopItem(name="Avatar Sofía", description="Sofía - Chica golden elegante.", price=50, category="avatar", image="avatar_4.svg"),
        ShopItem(name="Avatar Don Alberto", description="Don Alberto - Caballero formal.", price=50, category="avatar", image="avatar_5.svg"),
        ShopItem(name="Avatar Lucía", description="Lucía - Chica deportista.", price=50, category="avatar", image="avatar_6.svg"),
        ShopItem(name="Avatar Camila", description="Camila - Chica pelirroja.", price=50, category="avatar", image="avatar_7.svg"),
        ShopItem(name="Avatar Mateo", description="Mateo - Joven con gorra.", price=50, category="avatar", image="avatar_8.svg"),
        # Otros productos
        ShopItem(name="Tema Oscuro", description="Activa el modo oscuro en tu dashboard.", price=120, category="theme", image=None),
        ShopItem(name="Fondo Estelar", description="Fondo espacial para tu perfil.", price=40, category="background", image=None),
        ShopItem(name="Ícono Especial", description="Un ícono exclusivo para tus hábitos.", price=30, category="icon", image=None),
        ShopItem(name="Pack de Sonidos", description="Efectos de sonido al completar hábitos.", price=150, category="sound", image=None),
    ]

    for p in products:
        db.session.add(p)
    db.session.commit()

    flash('🎉 ¡Tienda poblada con 12 productos!', 'success')
    return redirect(url_for('shop'))


# ====== MÓDULO DE AHORROS ======

@app.route("/savings")
@login_required
def savings():
    """Dashboard principal del sistema de ahorros."""
    user_id = session['user_id']
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    # Categorías del usuario + globales
    categories = Category.query.filter(
        (Category.user_id == user_id) | (Category.user_id.is_(None))
    ).order_by(Category.type, Category.name).all()

    # Transacciones del usuario (ordenadas por fecha descendente)
    transactions = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()

    # Metas de ahorro
    goals = SavingsGoal.query.filter_by(user_id=user_id).order_by(SavingsGoal.created_at.desc()).all()

    # Calcular totales
    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
    balance = total_income - total_expenses

    today = date.today()

    return render_template("savings.html",
                           categories=categories,
                           transactions=transactions,
                           goals=goals,
                           total_income=total_income,
                           total_expenses=total_expenses,
                           balance=balance,
                           coins=progress.coins if progress else 0,
                           today=today)


@app.route("/savings/add_transaction", methods=['POST'])
@login_required
def add_transaction():
    """Agregar una nueva transacción (ingreso o gasto)."""
    user_id = session['user_id']
    amount = request.form.get('amount', 0, type=float)
    category_id = request.form.get('category_id', 0, type=int)
    description = request.form.get('description', '').strip()
    transaction_date = request.form.get('date', date.today().isoformat())
    trans_type = request.form.get('type', 'expense')

    if amount <= 0:
        flash('El monto debe ser mayor a cero.', 'danger')
        return redirect(url_for('savings'))

    if not category_id:
        flash('Debes seleccionar una categoría.', 'danger')
        return redirect(url_for('savings'))

    try:
        trans_date = date.fromisoformat(transaction_date)
    except (ValueError, TypeError):
        trans_date = date.today()

    tx = Transaction(
        user_id=user_id,
        category_id=category_id,
        amount=amount,
        description=description,
        date=trans_date,
        type=trans_type
    )
    db.session.add(tx)
    db.session.commit()

    flash(f'✅ {"Ingreso" if trans_type == "income" else "Gasto"} registrado: ${amount:.2f}', 'success')
    return redirect(url_for('savings'))


@app.route("/savings/delete_transaction/<int:tx_id>")
@login_required
def delete_transaction(tx_id):
    """Eliminar una transacción."""
    user_id = session['user_id']
    tx = Transaction.query.filter_by(id=tx_id, user_id=user_id).first_or_404()
    db.session.delete(tx)
    db.session.commit()
    flash('🗑️ Transacción eliminada.', 'success')
    return redirect(url_for('savings'))


@app.route("/savings/add_goal", methods=['POST'])
@login_required
def add_savings_goal():
    """Crear una nueva meta de ahorro."""
    user_id = session['user_id']
    name = request.form.get('name', '').strip()
    target_amount = request.form.get('target_amount', 0, type=float)
    current_amount = request.form.get('current_amount', 0, type=float)
    deadline_str = request.form.get('deadline', '')
    color = request.form.get('color', '#1cc88a')

    if not name or target_amount <= 0:
        flash('Nombre y monto objetivo son obligatorios.', 'danger')
        return redirect(url_for('savings'))

    deadline = None
    if deadline_str:
        try:
            deadline = date.fromisoformat(deadline_str)
        except (ValueError, TypeError):
            deadline = None

    goal = SavingsGoal(
        user_id=user_id,
        name=name,
        target_amount=target_amount,
        current_amount=current_amount,
        deadline=deadline,
        color=color
    )
    db.session.add(goal)
    db.session.commit()

    flash(f'🎯 Meta de ahorro "{name}" creada.', 'success')
    return redirect(url_for('savings'))


@app.route("/savings/update_goal/<int:goal_id>", methods=['POST'])
@login_required
def update_savings_goal(goal_id):
    """Actualizar el progreso de una meta de ahorro."""
    user_id = session['user_id']
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first_or_404()

    current_amount = request.form.get('current_amount', 0, type=float)
    goal.current_amount = max(0, current_amount)

    # Verificar si la meta se acaba de completar (antes no estaba completada)
    was_completed = goal.completed
    goal.completed = goal.current_amount >= goal.target_amount

    # Recompensa de monedas al completar la meta
    coins_awarded = 0
    if goal.completed and not was_completed:
        # Calcular monedas: base 50 + bonus según dificultad (target_amount / 100)
        coins_awarded = 50 + min(int(goal.target_amount / 100), 200)
        user = User.query.get(user_id)
        user.coins = (user.coins or 0) + coins_awarded
        # Registrar transacción de monedas
        tx = CoinTransaction(
            user_id=user_id,
            amount=coins_awarded,
            description=f'Meta de ahorro completada: {goal.name}',
            tx_type='earn'
        )
        db.session.add(tx)

    db.session.commit()

    if coins_awarded > 0:
        flash(f'🎉 Meta "{goal.name}" completada! Has ganado {coins_awarded} monedas BetterMe!', 'success')
    else:
        flash(f'💰 Meta "{goal.name}" actualizada: ${goal.current_amount:.2f}/${goal.target_amount:.2f}', 'success')
    return redirect(url_for('savings'))


@app.route("/savings/delete_goal/<int:goal_id>", methods=['POST'])
@login_required
def delete_savings_goal(goal_id):
    """Eliminar una meta de ahorro."""
    user_id = session['user_id']
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first_or_404()
    name = goal.name
    db.session.delete(goal)
    db.session.commit()
    flash(f'🗑️ Meta "{name}" eliminada.', 'success')
    return redirect(url_for('savings'))


# ─── API para gráficas del módulo de ahorros ─────────────────────

@app.route("/api/savings/balance_history")
@login_required
def api_savings_balance_history():
    """Devuelve datos para la gráfica de capital a través del tiempo (últimos 30 días)."""
    user_id = session['user_id']
    days = request.args.get('days', 30, type=int)
    days = max(7, min(days, 90))

    today = date.today()
    dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

    labels = []
    data = []

    for d in dates:
        label = d.strftime('%d/%m')
        labels.append(label)

        # Calcular balance hasta esa fecha
        income = db.session.query(db.func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id, Transaction.type == 'income', Transaction.date <= d).scalar() or 0
        expenses = db.session.query(db.func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id, Transaction.type == 'expense', Transaction.date <= d).scalar() or 0
        balance = income - expenses
        data.append(round(balance, 2))

    return jsonify({
        'labels': labels,
        'data': data
    })


@app.route("/api/savings/category_pie")
@login_required
def api_savings_category_pie():
    """Devuelve datos para la gráfica de pastel de gastos por categoría."""
    user_id = session['user_id']

    # Obtener gastos agrupados por categoría
    results = db.session.query(
        Category.name,
        Category.color,
        Category.icon,
        db.func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.category_id == Category.id)\
     .filter(Transaction.user_id == user_id, Transaction.type == 'expense')\
     .group_by(Category.id)\
     .order_by(db.func.sum(Transaction.amount).desc()).all()

    labels = [r.name for r in results]
    data = [round(r.total, 2) for r in results]
    colors = [r.color for r in results]
    icons = [r.icon for r in results]

    return jsonify({
        'labels': labels,
        'data': data,
        'colors': colors,
        'icons': icons
    })


@app.route("/api/savings/goals_progress")
@login_required
def api_savings_goals_progress():
    """Devuelve datos de progreso de metas de ahorro."""
    user_id = session['user_id']
    goals = SavingsGoal.query.filter_by(user_id=user_id).all()

    data = []
    for g in goals:
        data.append({
            'id': g.id,
            'name': g.name,
            'target': g.target_amount,
            'current': g.current_amount,
            'percentage': g.progress_percentage(),
            'color': g.color,
            'completed': g.completed,
            'deadline': g.deadline.isoformat() if g.deadline else None
        })

    return jsonify({'goals': data})


# ─── RUTA DE DIAGNOSTICO (para depurar Render) ────────────────────

@app.route("/debug-db")
def debug_db():
    """Muestra el estado de la base de datos en produccion."""
    import json
    info = {
        'is_production': is_production,
        'db_uri_type': 'PostgreSQL' if is_production else 'SQLite',
    }
    try:
        db.session.execute(db.text('SELECT 1'))
        info['db_connection'] = 'OK'
    except Exception as e:
        info['db_connection'] = f'ERROR: {e}'

    try:
        info['tables'] = {}
        for table in ['user', 'habit', 'user_habit', 'user_progress', 'shop_item',
                       'coin_transaction', 'category', 'transaction', 'savings_goal']:
            try:
                count = db.session.execute(db.text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
                info['tables'][table] = count
            except Exception as e:
                info['tables'][table] = f'ERROR: {e}'

        # Buscar usuario test
        test_user = User.query.filter_by(email='test@test.com').first()
        if test_user:
            info['test_user'] = {
                'id': test_user.id,
                'name': test_user.name,
                'email': test_user.email,
                'avatar': test_user.avatar,
            }
            prog = UserProgress.query.filter_by(user_id=test_user.id).first()
            info['test_user_progress'] = {
                'coins': prog.coins if prog else 'N/A',
                'streak': prog.streak if prog else 'N/A',
            }
        else:
            info['test_user'] = 'NO EXISTE'
            info['test_user_progress'] = 'N/A'

        # Buscar cualquier usuario
        all_users = User.query.all()
        info['total_users'] = len(all_users)
    except Exception as e:
        info['query_error'] = f'{type(e).__name__}: {e}'

    return jsonify(info)


if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=not is_production)
