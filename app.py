from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date
from functools import wraps
import os
import secrets
from dotenv import load_dotenv
from flask_mail import Mail, Message

from models import db, User, Task, Habit, UserHabit, UserProgress

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
    # Obtener hábitos disponibles para mostrar en el formulario
    available_habits = Habit.query.all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validaciones
        if not name or not email or not password:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template("register.html", habits=available_habits)

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template("register.html", habits=available_habits)

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template("register.html", habits=available_habits)

        # Verificar si el email ya está registrado
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Ya existe una cuenta con este correo electrónico.', 'danger')
            return render_template("register.html", habits=available_habits)

        # Obtener hábitos seleccionados por el usuario
        selected_habit_ids = request.form.getlist('habits')
        # Convertir a enteros
        selected_habit_ids = [int(hid) for hid in selected_habit_ids if hid.isdigit()]

        if not selected_habit_ids:
            flash('Debes seleccionar al menos un hábito diario.', 'danger')
            return render_template("register.html", habits=available_habits)

        # Crear usuario
        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Para obtener el ID del usuario

        # Crear progreso inicial para el usuario
        progress = UserProgress(user_id=user.id, coins=100, streak=0)
        db.session.add(progress)

        # Crear UserHabit solo para los hábitos seleccionados
        for habit_id in selected_habit_ids:
            uh = UserHabit(user_id=user.id, habit_id=habit_id, completed=False)
            db.session.add(uh)

        db.session.commit()

        flash('¡Cuenta creada exitosamente! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template("register.html", habits=available_habits)


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
def avatars():
    """Galería de avatares."""
    return render_template("avatars.html")


# ─── Rutas del Dashboard (protegidas) ───────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard principal con tareas, hábitos y progreso."""
    user_id = session['user_id']

    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.created_at.desc()).all()
    user_habits_data = get_user_habits(user_id)
    progress = UserProgress.query.filter_by(user_id=user_id).first()

    # Calcular estadísticas basadas en UserHabit
    total_habits = len(user_habits_data)
    completed_habits = sum(1 for uh in user_habits_data if uh['user_habit'].completed)
    progress_percentage = int((completed_habits / total_habits * 100)) if total_habits > 0 else 0

    return render_template("dashboard.html",
                           tasks=tasks,
                           user_habits_data=user_habits_data,
                           coins=progress.coins if progress else 100,
                           streak=progress.streak if progress else 0,
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


@app.route("/toggle_habit/<int:habit_id>")
@login_required
def toggle_habit(habit_id):
    user_id = session['user_id']

    # Buscar o crear el UserHabit para este usuario y hábito
    uh = UserHabit.query.filter_by(user_id=user_id, habit_id=habit_id).first()
    if uh is None:
        uh = UserHabit(user_id=user_id, habit_id=habit_id, completed=False)
        db.session.add(uh)
        db.session.flush()

    uh.completed = not uh.completed
    uh.completed_date = date.today() if uh.completed else None

    habit = Habit.query.get_or_404(habit_id)
    progress = UserProgress.query.filter_by(user_id=user_id).first()
    if progress:
        progress.update_streak()
        if uh.completed:
            progress.coins += habit.coins
        else:
            progress.coins = max(0, progress.coins - (habit.coins // 2))
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


if __name__ == "__main__":
    app.run(debug=True)
