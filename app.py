from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'mannu734'

# SQLite database configuration
DATABASE = 'users.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# MongoDB configuration
client = MongoClient('mongodb_connection_string')
db_mongo = client['database_name']
collection = db_mongo['collection_name']

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()

        if user:
            session['username'] = username
            return redirect(url_for('sensor_data'))
        else:
            return 'Invalid username or password'

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Process registration form submission
        username = request.form['username']
        password = request.form['password']

        # Add user to the SQLite database
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        db.commit()

        # Redirect to login page after registration
        return redirect(url_for('home'))

    # Render registration form for GET requests
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return f'Welcome, {session["username"]}!'
    else:
        return redirect(url_for('home'))

@app.route('/sensor_data')
def sensor_data():
    # Fetch data from MongoDB
    data = collection.find()
    # Pass data to the template
    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)
