import secrets
import os
import pickle
import numpy as np
from flask import Flask, render_template, redirect, request, session, url_for, flash, jsonify
from pymongo import MongoClient
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from bson import ObjectId
from datetime import datetime, timedelta

#libraries for course recom
from os import read
import pandas as pd
import neattext.functions as nfx
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity, linear_kernel
from dashboard import getvaluecounts, getlevelcount, getsubjectsperlevel, yearwiseprofit


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

@app.route('/profile',methods=['GET','POST'])
def profile():
    if current_user.is_authenticated:  # Check if the user is authenticated
        # user_data = users.find_one({'username': current_user.username})

        user_details = users_collection.find_one({'username':current_user.username})
        
        return render_template('profile.html', user_details=user_details)

    return render_template('profile.html')


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


#course recommendation system start


def getcosinemat(df):

    countvect = CountVectorizer()
    cvmat = countvect.fit_transform(df['Clean_title'])
    return cvmat

# getting the title which doesn't contain stopwords and all which we removed with the help of nfx


def getcleantitle(df):

    df['Clean_title'] = df['course_title'].apply(nfx.remove_stopwords)

    df['Clean_title'] = df['Clean_title'].apply(nfx.remove_special_characters)

    return df


def cosinesimmat(cv_mat):

    return cosine_similarity(cv_mat)


def readdata():

    df = pd.read_csv('UdemyCleanedTitle.csv')
    return df

# this is the main recommendation logic for a particular title which is choosen


def recommend_course(df, title, cosine_mat, numrec):

    course_index = pd.Series(
        df.index, index=df['course_title']).drop_duplicates()

    index = course_index[title]

    scores = list(enumerate(cosine_mat[index]))

    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    selected_course_index = [i[0] for i in sorted_scores[1:]]

    selected_course_score = [i[1] for i in sorted_scores[1:]]

    rec_df = df.iloc[selected_course_index]

    rec_df['Similarity_Score'] = selected_course_score

    final_recommended_courses = rec_df[[
        'course_title', 'Similarity_Score', 'url', 'price', 'num_subscribers']]

    return final_recommended_courses.head(numrec)

# this will be called when a part of the title is used,not the complete title!


def searchterm(term, df):
    result_df = df[df['course_title'].str.contains(term)]
    top6 = result_df.sort_values(by='num_subscribers', ascending=False).head(6)
    return top6


# extract features from the recommended dataframe

def extractfeatures(recdf):

    course_url = list(recdf['url'])
    course_title = list(recdf['course_title'])
    course_price = list(recdf['price'])

    return course_url, course_title, course_price

@app.route('/')
def home():
    return render_template('index_course.html')


@app.route('/index_course', methods=['GET', 'POST'])
def hello_world():

    if request.method == 'POST':

        my_dict = request.form
        titlename = my_dict['course']
        print(titlename)

        try:
            df = readdata()
            df = getcleantitle(df)
            cvmat = getcosinemat(df)

            num_rec = 6
            cosine_mat = cosinesimmat(cvmat)

            recdf = recommend_course(df, titlename, cosine_mat, num_rec)

            course_url, course_title, course_price = extractfeatures(recdf)

            dictmap = dict(zip(course_title, course_url))

            if len(dictmap) != 0:
                return render_template('index_course.html', coursemap=dictmap, coursename=titlename, showtitle=True)
            else:
                return render_template('index_course.html', showerror=True, coursename=titlename)

        except Exception as e:
            # Log the error for debugging purposes
            print(f"An error occurred: {e}")

            # Attempt to handle the partial title search
            try:
                resultdf = searchterm(titlename, df)
                if resultdf.shape[0] > 6:
                    resultdf = resultdf.head(6)

                course_url, course_title, course_price = extractfeatures(resultdf)
                coursemap = dict(zip(course_title, course_url))

                if len(coursemap) != 0:
                    return render_template('index_course.html', coursemap=coursemap, coursename=titlename, showtitle=True)
                else:
                    return render_template('index_course.html', showerror=True, coursename=titlename)

            except Exception as e:
                # Log any error that occurs during partial title search
                print(f"Error during title search: {e}")
                return render_template('index_course.html', showerror=True, coursename=titlename)

    return render_template('index_course.html')



@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():

    df = readdata()
    valuecounts = getvaluecounts(df)

    levelcounts = getlevelcount(df)

    subjectsperlevel = getsubjectsperlevel(df)

    yearwiseprofitmap, subscriberscountmap, profitmonthwise, monthwisesub = yearwiseprofit(
        df)

    return render_template('dashboard.html', valuecounts=valuecounts, levelcounts=levelcounts,
                           subjectsperlevel=subjectsperlevel, yearwiseprofitmap=yearwiseprofitmap, subscriberscountmap=subscriberscountmap, profitmonthwise=profitmonthwise, monthwisesub=monthwisesub)


#course recommendation system end


#BOOK RECOMMENDATION SYSTEM START

# Load your data

# Load your data
popular_df = pickle.load(open('popular.pkl', 'rb'))
pt = pickle.load(open('pt.pkl', 'rb'))
books = pickle.load(open('books.pkl', 'rb'))
similarity_scores = pickle.load(open('similarity_scores.pkl', 'rb'))

# Home route
@app.route('/')
def homepage():
    return render_template('index.html')

# Book recommendation system routes
@app.route('/recommendation', methods=['GET', 'POST'])
def recommend_books():
    if request.method == 'POST':
        user_input = request.form.get('user_input').lower()

        # Initialize variables for book and author matching
        book_found = None
        author_found = None

        # Search for the book in title
        for book in pt.index:
            if user_input in book.lower():
                book_found = book
                break

        # Search for the author in the books dataset
        if not book_found:
            for author in books['Book-Author'].unique():
                if user_input in author.lower():
                    author_found = author
                    break

        data = []

        # If a book is found, recommend similar books
        if book_found:
            index = np.where(pt.index == book_found)[0][0]
            similar_items = sorted(list(enumerate(similarity_scores[index])), key=lambda x: x[1], reverse=True)[1:5]

            for i in similar_items:
                item = []
                temp_df = books[books['Book-Title'] == pt.index[i[0]]]
                item.extend(list(temp_df.drop_duplicates('Book-Title')['Book-Title'].values))
                item.extend(list(temp_df.drop_duplicates('Book-Title')['Book-Author'].values))
                item.extend(list(temp_df.drop_duplicates('Book-Title')['Image-URL-M'].values))
                data.append(item)

        # If an author is found, recommend books by the author
        elif author_found:
            author_books = books[books['Book-Author'] == author_found].drop_duplicates('Book-Title')

            for _, row in author_books.iterrows():
                item = []
                item.append(row['Book-Title'])
                item.append(row['Book-Author'])
                item.append(row['Image-URL-M'])
                data.append(item)

        # If no match found, display a message
        if not data:
            error = "No Book or Author found. Please try again."
            book_name = list(popular_df['Book-Title'].values)
            author = list(popular_df['Book-Author'].values)
            image = list(popular_df['Image-URL-M'].values)
            votes = list(popular_df['num_ratings'].values)
            rating = list(popular_df['avg_rating'].values)
            return render_template('recommendation.html', error=error, book_name=book_name, author=author, image=image, votes=votes, rating=rating)

        book_name = list(popular_df['Book-Title'].values)
        author = list(popular_df['Book-Author'].values)
        image = list(popular_df['Image-URL-M'].values)
        votes = list(popular_df['num_ratings'].values)
        rating = list(popular_df['avg_rating'].values)
        return render_template('recommendation.html', data=data, book_name=book_name, author=author, image=image, votes=votes, rating=rating)

    else:
        # Load top 50 books data
        book_name = list(popular_df['Book-Title'].values)
        author = list(popular_df['Book-Author'].values)
        image = list(popular_df['Image-URL-M'].values)
        votes = list(popular_df['num_ratings'].values)
        rating = list(popular_df['avg_rating'].values)

        return render_template('recommendation.html',
                               book_name=book_name,
                               author=author,
                               image=image,
                               votes=votes,
                               rating=rating)

#BOOK RECOMMENDATION END


if __name__ == '__main__':
    app.run(debug=True, port=5001)
