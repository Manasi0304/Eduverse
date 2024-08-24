from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recommend')
def recommend():
    return render_template('recommend.html')

@app.route('/result')
def result():
    return render_template('result.html')

@app.route('/testimonials')
def testimonials():
    return render_template('testimonials.html')

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
    

