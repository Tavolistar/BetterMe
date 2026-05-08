from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """Modelo de usuario para autenticación."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    avatar = db.Column(db.String(50), default='undraw_profile.svg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    tasks = db.relationship('Task', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    progress = db.relationship('UserProgress', backref='owner', uselist=False, cascade='all, delete-orphan')
    habits = db.relationship('UserHabit', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Genera el hash de la contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica la contraseña contra el hash almacenado."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.id}: {self.email}>'


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    def __repr__(self):
        return f'<Task {self.id}: {self.text}>'


class Habit(db.Model):
    """Modelo de hábitos.
    
    - Hábitos predefinidos (globales): is_custom=False, user_id=None
    - Hábitos personalizados (creados por usuario): is_custom=True, user_id=<id>
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    coins = db.Column(db.Integer, default=10)  # MO-02: +10 monedas por hábito
    is_custom = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

    # Relación con el progreso por usuario
    user_habits = db.relationship('UserHabit', backref='habit', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Habit {self.id}: {self.name} custom={self.is_custom}>'


class UserHabit(db.Model):
    """Progreso de un hábito específico para un usuario específico."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False, index=True)
    completed = db.Column(db.Boolean, default=False)
    completed_date = db.Column(db.Date, nullable=True)

    __table_args__ = (db.UniqueConstraint('user_id', 'habit_id', name='uq_user_habit'),)

    def __repr__(self):
        return f'<UserHabit user={self.user_id} habit={self.habit_id} completed={self.completed}>'


class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True, index=True)
    coins = db.Column(db.Integer, default=100)
    streak = db.Column(db.Integer, default=0)
    last_activity = db.Column(db.Date, default=date.today)

    def update_streak(self):
        today = date.today()
        if self.last_activity != today:
            if self.last_activity == date.fromordinal(today.toordinal() - 1):
                self.streak += 1
            else:
                self.streak = 1
            self.last_activity = today

    def __repr__(self):
        return f'<UserProgress user={self.user_id}: {self.coins} coins, {self.streak} streak>'


class HabitLog(db.Model):
    """Registro diario de cumplimiento de hábitos para gráficas e historial."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    completed = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'habit_id', 'date', name='uq_user_habit_date'),
    )

    user = db.relationship('User', backref=db.backref('habit_logs', lazy='dynamic'))
    habit = db.relationship('Habit', backref=db.backref('habit_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<HabitLog user={self.user_id} habit={self.habit_id} date={self.date} completed={self.completed}>'


class ShopItem(db.Model):
    """Producto disponible en la tienda de BetterMe."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    price = db.Column(db.Integer, nullable=False, default=50)
    image = db.Column(db.String(100), nullable=True)  # nombre del archivo de imagen
    category = db.Column(db.String(50), default='avatar')  # avatar, fondo, icono, etc.
    stock = db.Column(db.Integer, default=-1)  # -1 = ilimitado

    purchases = db.relationship('UserPurchase', backref='item', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ShopItem {self.id}: {self.name} ${self.price}>'


class CoinTransaction(db.Model):
    """Registro de transacciones de monedas (MO-05)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False)  # positivo = ganó, negativo = gastó
    concept = db.Column(db.String(200), nullable=False)  # ej: "Hábito: Beber agua", "Compra: Avatar 3"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('coin_transactions', lazy='dynamic'))

    def __repr__(self):
        return f'<CoinTransaction user={self.user_id} amount={self.amount} concept={self.concept}>'


class UserPurchase(db.Model):
    """Compra realizada por un usuario en la tienda."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'), nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('purchases', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'item_id', name='uq_user_item'),)

    def __repr__(self):
        return f'<UserPurchase user={self.user_id} item={self.item_id}>'
