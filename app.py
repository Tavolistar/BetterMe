from flask import Flask, render_template, request, redirect, url_for, session
from datetime import date
import os
from dotenv import load_dotenv

from models import db, Task, Habit, UserProgress

# Cargar variables de entorno
load_dotenv()

# Obtener la ruta base del proyecto
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, instance_path=os.path.join(basedir, 'instance'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'clave_secreta_por_defecto_cambiar_en_produccion')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///betterme.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar SQLAlchemy con la app
db.init_app(app)

# Crear tablas si no existen
with app.app_context():
    db.create_all()

    # Inicializar hábitos predefinidos si no existen
    if Habit.query.count() == 0:
        default_habits = [
            Habit(name='Beber agua', description='Tomar al menos 8 vasos de agua al día', coins=5),
            Habit(name='Ejercicio 30 min', description='Realizar actividad física por 30 minutos', coins=10),
            Habit(name='Leer 20 páginas', description='Leer 20 páginas de un libro', coins=8)
        ]
        db.session.bulk_save_objects(default_habits)
        db.session.commit()

    # Inicializar progreso del usuario si no existe
    if UserProgress.query.filter_by(user_id='default_user').first() is None:
        progress = UserProgress(user_id='default_user', coins=100, streak=0)
        db.session.add(progress)
        db.session.commit()


# ─── Rutas públicas ────────────────────────────────────────────────

@app.route("/")
def index():
    """Página de inicio / landing page."""
    return render_template("index.html")


@app.route("/login")
def login():
    """Página de inicio de sesión."""
    return render_template("login.html")


@app.route("/register")
def register():
    """Página de registro."""
    return render_template("register.html")


@app.route("/avatars")
def avatars():
    """Galería de avatares."""
    return render_template("avatars.html")


# ─── Rutas del Dashboard ───────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    """Dashboard principal con tareas, hábitos y progreso."""
    tasks = Task.query.filter_by(user_id='default_user').order_by(Task.created_at.desc()).all()
    habits = Habit.query.all()
    progress = UserProgress.query.filter_by(user_id='default_user').first()

    completed_habits = Habit.query.filter_by(completed=True).count()
    total_habits = Habit.query.count()
    progress_percentage = int((completed_habits / total_habits * 100)) if total_habits > 0 else 0

    return render_template("dashboard.html",
                           tasks=tasks,
                           habits=habits,
                           coins=progress.coins if progress else 100,
                           streak=progress.streak if progress else 0,
                           progress_percentage=progress_percentage,
                           completed_habits=completed_habits,
                           total_habits=total_habits)


@app.route("/add_task", methods=['POST'])
def add_task():
    task_text = request.form.get('task_text')
    if task_text:
        new_task = Task(text=task_text, user_id='default_user')
        db.session.add(new_task)
        db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/delete_task/<int:task_id>")
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/toggle_task/<int:task_id>")
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.completed = not task.completed

    progress = UserProgress.query.filter_by(user_id='default_user').first()
    if progress:
        progress.update_streak()
        if task.completed:
            progress.coins += 10
        else:
            progress.coins = max(0, progress.coins - 5)
        db.session.commit()

    return redirect(url_for('dashboard'))


@app.route("/toggle_habit/<int:habit_id>")
def toggle_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    habit.completed = not habit.completed
    habit.completed_date = date.today() if habit.completed else None

    progress = UserProgress.query.filter_by(user_id='default_user').first()
    if progress:
        progress.update_streak()
        if habit.completed:
            progress.coins += habit.coins
        else:
            progress.coins = max(0, progress.coins - (habit.coins // 2))
        db.session.commit()

    return redirect(url_for('dashboard'))


@app.route("/reset_day")
def reset_day():
    habits = Habit.query.all()
    for habit in habits:
        habit.completed = False
        habit.completed_date = None

    progress = UserProgress.query.filter_by(user_id='default_user').first()
    if progress:
        progress.update_streak()

    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route("/add_sample_tasks")
def add_sample_tasks():
    sample_tasks = [
        "Meditar 10 minutos",
        "Escribir en el diario",
        "Planificar el día siguiente",
        "Aprender algo nuevo"
    ]

    for task_text in sample_tasks:
        if not Task.query.filter_by(text=task_text, user_id='default_user').first():
            new_task = Task(text=task_text, user_id='default_user')
            db.session.add(new_task)

    db.session.commit()
    return redirect(url_for('dashboard'))


if __name__ == "__main__":
    app.run(debug=True)
