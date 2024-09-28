import secrets
import os
import pickle
import numpy as np
from flask import Flask, render_template, redirect, request, session, url_for, flash, jsonify
from pymongo import MongoClient
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from bson import ObjectId
from datetime import datetime, timedelta

app = Flask(__name__)

# Set the secret key securely
secret_key = secrets.token_hex(16)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secret_key)

client = MongoClient('mongodb://localhost:27017')
db = client['eduverse']
users_collection = db['users']

login_manager = LoginManager()
login_manager.init_app(app)

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, username):
        self.username = username

    def get_id(self):
        return str(self.username)

# Load user from database
@login_manager.user_loader
def load_user(username):
    user_data = users_collection.find_one({'username': username})
    if user_data:
        return User(user_data['username'])
    return None

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        dob = request.form['dob']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        mobile = request.form['mobile']

        if users_collection.find_one({'username': username}):
            flash('Username already taken. Please choose a different username.', 'error')
            return redirect(url_for('signup'))

        new_user = {
            'fullname': fullname,
            'dob': dob,
            'username': username,
            'email': email,
            'password': password,
            'mobile': mobile
        }
        users_collection.insert_one(new_user)
        flash('Signup successful. You can now login.', 'success')
        return redirect(url_for('login'))  # Redirect to login after signup


    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_data = users_collection.find_one({'username': username, 'password': password})

        if user_data:
            user = User(user_data['username'])
            login_user(user)
            return redirect(url_for('recommend'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))   

# Load the scaler, label encoder, model, and class names ====================
try:
    scaler = pickle.load(open("Models/scaler.pkl", 'rb'))
except (EOFError, FileNotFoundError) as e:
    print("Scaler not found or corrupted. Please ensure the scaler is available.")
    scaler = None  # Or create a new one if required

try:
    model = pickle.load(open("Models/model.pkl", 'rb'))
except (EOFError, FileNotFoundError) as e:
    print("Model not found or corrupted. Please ensure the model is available.")
    model = None  # Or handle the missing model case

class_names = ['Lawyer', 'Doctor', 'Government Officer', 'Artist', 'Unknown',
               'Software Engineer', 'Teacher', 'Business Owner', 'Scientist',
               'Banker', 'Writer', 'Accountant', 'Designer',
               'Construction Engineer', 'Game Developer', 'Stock Investor',
               'Real Estate Developer']

# Recommendations ===========================================================
def Recommendations(gender, part_time_job, absence_days, extracurricular_activities,
                    weekly_self_study_hours, math_score, history_score, physics_score,
                    chemistry_score, biology_score, english_score, geography_score,
                    total_score, average_score):
    if scaler is None or model is None:
        return "Scaler or model not available. Please check the system configuration."

    # Encode categorical variables
    gender_encoded = 1 if gender.lower() == 'female' else 0
    part_time_job_encoded = 1 if part_time_job else 0
    extracurricular_activities_encoded = 1 if extracurricular_activities else 0

    # Create feature array
    feature_array = np.array([[gender_encoded, part_time_job_encoded, absence_days, extracurricular_activities_encoded,
                               weekly_self_study_hours, math_score, history_score, physics_score,
                               chemistry_score, biology_score, english_score, geography_score, total_score,
                               average_score]])

    # Scale features
    scaled_features = scaler.transform(feature_array)

    # Predict using the model
    probabilities = model.predict_proba(scaled_features)

    # Get top three predicted classes along with their probabilities
    top_classes_idx = np.argsort(-probabilities[0])[:3]
    top_classes_names_probs = [(class_names[idx], probabilities[0][idx]) for idx in top_classes_idx]

    return top_classes_names_probs

# ---------- index page ----------- 
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

# ------------- profile ------------- 
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_data = users_collection.find_one({'username': current_user.username})
    return render_template('profile.html', user_data=user_data)

# ---------- recommend ----------- 
@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    user_data = None  # Initialize user_data to None

    if current_user.is_authenticated:  # Check if the user is authenticated
        user_data = users_collection.find_one({'username': current_user.username})

    return render_template('recommend.html', user_data=user_data)

# ---------- resources ----------- 
@app.route('/resources', methods=['GET', 'POST'])
def resources():
    user_data = None  # Initialize user_data to None

    if current_user.is_authenticated:  # Check if the user is authenticated
        user_data = users_collection.find_one({'username': current_user.username})

    return render_template('resources.html', user_data=user_data)

# ---------- result ----------- 
@app.route('/result', methods=['GET', 'POST'])
def result():
    user_data = None  # Initialize user_data to None

    if current_user.is_authenticated:  # Check if the user is authenticated
        user_data = users_collection.find_one({'username': current_user.username})

    return render_template('result.html', user_data=user_data)

@app.route('/pred', methods=['POST', 'GET'])
def pred():
    if request.method == 'POST':
        gender = request.form['gender']
        part_time_job = request.form['part_time_job'] == 'true'
        absence_days = int(request.form['absence_days'])
        extracurricular_activities = request.form['extracurricular_activities'] == 'true'
        weekly_self_study_hours = int(request.form['weekly_self_study_hours'])
        math_score = int(request.form['math_score'])
        history_score = int(request.form['history_score'])
        physics_score = int(request.form['physics_score'])
        chemistry_score = int(request.form['chemistry_score'])
        biology_score = int(request.form['biology_score'])
        english_score = int(request.form['english_score'])
        geography_score = int(request.form['geography_score'])
        total_score = float(request.form['total_score'])
        average_score = float(request.form['average_score'])

        recommendations = Recommendations(gender, part_time_job, absence_days, extracurricular_activities,
                                          weekly_self_study_hours, math_score, history_score, physics_score,
                                          chemistry_score, biology_score, english_score, geography_score,
                                          total_score, average_score)

        return render_template('result.html', recommendations=recommendations)
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
