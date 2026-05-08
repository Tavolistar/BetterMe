from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import date, timedelta, datetime
from functools import wraps
import os
import secrets
from dotenv import load_dotenv
from flask_mail import Mail, Message

from models import db, User, Task, Habit, UserHabit, UserProgress, HabitLog, ShopItem, CoinTransaction, UserPurchase

# Cargar variables de entorno
load_dotenv()

# Obtener la ruta base del proyecto
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, instance_path=os.path.join(basedir, 'instance'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///betterme.db')
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


if __name__ == "__main__":
    app.run(debug=True)
