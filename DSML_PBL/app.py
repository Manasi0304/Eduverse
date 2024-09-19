import secrets
import os
import pickle
import numpy as np
from flask import Flask, render_template, redirect, request, session, url_for, flash,jsonify
from pymongo import MongoClient
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin,current_user
from bson import ObjectId
import cgi
from datetime import datetime,timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
app = Flask(__name__)




secret_key = secrets.token_hex(16)

# Set the secret key securely from environment variable or fallback to a default value
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secret_key)

client = MongoClient('mongodb://localhost:27017/')


app = Flask(__name__)

#sdfshh
# Generate a secure secret key
secret_key = secrets.token_hex(16)

# Set the secret key securely from environment variable or fallback to a default value
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
    else:
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
            print(user)
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


# Load the scaler, label encoder, model, and class names=====================
scaler = pickle.load(open("Models/scaler.pkl", 'rb'))
model = pickle.load(open("Models/model.pkl", 'rb'))
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

    # Get top five predicted classes along with their probabilities
    top_classes_idx = np.argsort(-probabilities[0])[:3]
    top_classes_names_probs = [(class_names[idx], probabilities[0][idx]) for idx in top_classes_idx]

    return top_classes_names_probs



# ---------- index page ----------- 
@app.route('/',methods=['GET','POST'])
def index():
    return render_template('index.html')




# ------------- profile ------------- 

@app.route('/profile',methods = ['GET','POST'])
def profile():

    user_data = users_collection.find_one({'username':current_user.username})
    return render_template('profile.html',user_data= user_data)    





# ---------- recommend ----------- 
@app.route('/recommend',methods=['GET','POST'])
def recommend():
    user_data = None  # Initialize user_data to None

    if current_user.is_authenticated:  # Check if the user is authenticated
        user_data = users_collection.find_one({'username': current_user.username})

    return render_template('recommend.html',user_data= user_data)



# ---------- resources ----------- 
@app.route('/resources',methods=['GET','POST'])
def resources():
    user_data = None  # Initialize user_data to None

    if current_user.is_authenticated:  # Check if the user is authenticated
        user_data = users_collection.find_one({'username': current_user.username})


    return render_template('resources.html',user_data= user_data)




# ---------- result ----------- 
@app.route('/result',methods=['GET','POST'])
def result():
    user_data = None  # Initialize user_data to None

    if current_user.is_authenticated:  # Check if the user is authenticated
        user_data = users_collection.find_one({'username': current_user.username})


    return render_template('result.html',user_data= user_data)



if __name__ == '__main__':
    app.run(debug=True, port=5001)