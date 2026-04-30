from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(50), default='default_user')

    def __repr__(self):
        return f'<Task {self.id}: {self.text}>'


class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    coins = db.Column(db.Integer, default=5)
    completed = db.Column(db.Boolean, default=False)
    completed_date = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f'<Habit {self.id}: {self.name}>'


class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), default='default_user')
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
        return f'<UserProgress {self.user_id}: {self.coins} coins, {self.streak} streak>'
