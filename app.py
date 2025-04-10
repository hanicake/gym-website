from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import re

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@localhost/dbname'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
app.config['SECRET_KEY'] = 'supersecretkey'
db = SQLAlchemy(app)

# ---------- MODELS ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    checkin_time = db.Column(db.DateTime, default=datetime.utcnow)
    checkout_time = db.Column(db.DateTime, nullable=True)
    time_spent = db.Column(db.Integer, nullable=True)  # in minutes

class Routine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    exercise = db.Column(db.String(200), nullable=False)

# ---------- ROUTES ----------

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')

        if re.search(r'\s', username):
            flash("Username cannot contain spaces.", "danger")
            return redirect(url_for('login'))

        user = User.query.filter_by(username=username).first()
        if not user:
            flash("No user exists with such username.", "danger")
            return redirect(url_for('login'))

        if user.password == password:
            session['user'] = username
            flash("Logged in successfully.", "success")
            return redirect(url_for('home'))
        else:
            flash("Incorrect password.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if re.search(r'\s', username):
            flash("Username cannot contain spaces.", "danger")
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "warning")
            return redirect(url_for('signup'))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('signup'))

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        session['user'] = username
        flash("Account created successfully. You're now logged in!", "success")
        return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session['user']
    last_log = Log.query.filter_by(username=username).order_by(Log.checkin_time.desc()).first()
    status_message = ""
    open_log = False

    if last_log:
        if last_log.checkout_time is None:
            open_log = True
            status_message = f"Checked in at {last_log.checkin_time.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            status_message = f"Checked out at {last_log.checkout_time.strftime('%Y-%m-%d %H:%M:%S')}"

    user_logs = Log.query.filter_by(username=username).order_by(Log.checkin_time.desc()).all()
    current_members = Log.query.filter_by(checkout_time=None).all()

    return render_template('home.html',
                           status_message=status_message,
                           logs=user_logs,
                           current_members=current_members,
                           open_log=open_log)

@app.route('/checkin', methods=['POST'])
def checkin():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session['user']
    now = datetime.utcnow()
    open_log = Log.query.filter_by(username=username, checkout_time=None).first()

    if open_log:
        # Check out
        open_log.checkout_time = now
        delta = (now - open_log.checkin_time)
        open_log.time_spent = int(delta.total_seconds() // 60)
        flash(f"Checked out at {now.strftime('%Y-%m-%d %H:%M:%S')}", "info")
    else:
        # Check in
        new_log = Log(username=username, checkin_time=now)
        db.session.add(new_log)
        flash(f"Checked in at {now.strftime('%Y-%m-%d %H:%M:%S')}", "success")

    db.session.commit()
    return redirect(url_for('home'))
@app.route('/routine', methods=['GET', 'POST'])
def routine():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session['user']
    
    if request.method == 'POST':
        day = request.form.get('day')
        exercise = request.form.get('exercise')
        if day and exercise:
            new_entry = Routine(username=username, day=day, exercise=exercise)
            db.session.add(new_entry)
            db.session.commit()
            flash("Exercise added!", "success")
        return redirect(url_for('routine'))

    routines_by_day = {}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
        routines_by_day[day] = Routine.query.filter_by(username=username, day=day).all()

    return render_template('routine.html', routines_by_day=routines_by_day)
# ---------- DB INIT ----------
if __name__ == '__main__':
    if not os.path.exists('gym.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True, port=8000)