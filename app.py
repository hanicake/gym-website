from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gym.db'
app.config['SECRET_KEY'] = 'supersecretkey'
db = SQLAlchemy(app)

# ---------- MODELS ----------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)  # username with no spaces
    password = db.Column(db.String(100), nullable=False)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    checkin_time = db.Column(db.DateTime, default=datetime.utcnow)
    checkout_time = db.Column(db.DateTime, nullable=True)
    time_spent = db.Column(db.Integer, nullable=True)  # in seconds

# ---------- ROUTES ----------

@app.route('/', methods=['GET'])
def index():
    # Redirect to login if not logged in; otherwise, go to home.
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Basic check: username should have no spaces
        if re.search(r'\s', username):
            flash("Username cannot contain spaces.", "danger")
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        if user:
            # Verify password
            if user.password == password:
                flash("Logged in successfully.", "success")
            else:
                flash("Incorrect password. Please try again.", "danger")
                return redirect(url_for('login'))
        else:
            # Create a new user
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash("Account created successfully.", "success")
        session['user'] = username
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

@app.route('/home', methods=['GET'])
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    # Get the latest log for status message
    last_log = Log.query.filter_by(username=username).order_by(Log.checkin_time.desc()).first()
    status_message = ""
    open_log = False
    if last_log:
        if last_log.checkout_time is None:
            open_log = True
            status_message = f"Checked in at {last_log.checkin_time.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            status_message = f"Checked out at {last_log.checkout_time.strftime('%Y-%m-%d %H:%M:%S')}"
    # Get all logs for current user
    user_logs = Log.query.filter_by(username=username).order_by(Log.checkin_time.desc()).all()
    # Get currently checked-in members (logs without checkout)
    current_members = Log.query.filter_by(checkout_time=None).all()
    return render_template('home.html', status_message=status_message, logs=user_logs, 
                           current_members=current_members, open_log=open_log)

@app.route('/checkin', methods=['POST'])
def checkin():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    now = datetime.now()
    # Check if user is currently checked in (i.e. has an open log)
    open_log_entry = Log.query.filter_by(username=username, checkout_time=None).first()
    if open_log_entry:
        # Check out: update the existing log
        open_log_entry.checkout_time = now
        delta = (now - open_log_entry.checkin_time).total_seconds()
        open_log_entry.time_spent = round(delta / 60, 2)  # in minutes, rounded to 2 decimal places

        flash(f"Checked out at {now.strftime('%Y-%m-%d %H:%M:%S')}", "info")
    else:
        # Check in: create a new log entry
        new_log = Log(username=username, checkin_time=now)
        db.session.add(new_log)
        flash(f"Checked in at {now.strftime('%Y-%m-%d %H:%M:%S')}", "success")
    db.session.commit()
    return redirect(url_for('home'))

# ---------- DATABASE INITIALIZATION ----------

if __name__ == '__main__':
    if not os.path.exists('gym.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True, port=8000)
