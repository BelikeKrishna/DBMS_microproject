from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_mysqldb import MySQL

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'       # MySQL server host
app.config['MYSQL_USER'] = 'root'            # MySQL username
app.config['MYSQL_PASSWORD'] = '1972'        # MySQL password
app.config['MYSQL_DB'] = 'project1'          # MySQL database name
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # Return results as dictionaries

mysql = MySQL(app)
app.secret_key = 'your_secret_key_here'

# Home Route
@app.route('/')
def loginpage():
    return render_template('login.html')

# Home Page (After Login)
@app.route('/home')
def home():
    if not session.get('logged_in'):  # Check if user is logged in
        return redirect(url_for('loginpage'))
    username = session.get('username')
    return render_template('index.html', username=username)

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user['id']  # Store user ID in session
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        mail = request.form.get('mail-id')
        cur = mysql.connection.cursor()

        # Check if username already exists
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cur.fetchone()

        if existing_user:
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        else:
            # Insert new user into the database
            cur.execute("INSERT INTO users (username, password, mail) VALUES (%s, %s, %s)", (username, password, mail))
            mysql.connection.commit()
            cur.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('loginpage'))

    return render_template('registration.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('loginpage'))

# Host Elections Route
@app.route('/host')
def host():
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    user_id = session.get('user_id')
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM elections WHERE host_id = %s", (user_id,))
    elections = cur.fetchall()
    cur.close()
    return render_template('host.html', elections=elections)

# Create Election Route
@app.route('/create_election', methods=['GET', 'POST'])
def create_election():
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        password = request.form.get('password')
        user_id = session.get('user_id')
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO elections (title, password, host_id) VALUES (%s, %s, %s)", (title, password, user_id))
        mysql.connection.commit()
        cur.close()
        flash('Election created successfully!', 'success')
        return redirect(url_for('host'))

    return render_template('create_election.html')

# Participate in Election Route
@app.route('/participate', methods=['GET', 'POST'])
def participate():
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        cur = mysql.connection.cursor()
        
        # Get election details
        cur.execute("""
            SELECT e.*, u.username as host_username 
            FROM elections e
            JOIN users u ON e.host_id = u.id
            WHERE e.password = %s
        """, (password,))
        election = cur.fetchone()
        
        if election:
            # Check if user already voted
            cur.execute("""
                SELECT * FROM participants 
                WHERE user_id = %s AND election_id = %s
            """, (session['user_id'], election['id']))
            
            if cur.fetchone():
                flash('You have already voted in this election', 'warning')
                cur.close()
                return redirect(url_for('results', election_id=election['id']))
            
            cur.close()
            return render_template('vote.html', 
                                election_id=election['id'],
                                election_title=election['title'],
                                host_username=election['host_username'])
        else:
            cur.close()
            flash('Invalid election password', 'error')
    
    return render_template('participate.html')

# Vote in Election Route
@app.route('/vote/<int:election_id>', methods=['GET', 'POST'])
def vote(election_id):
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    cur = mysql.connection.cursor()
    
    # Get election details for display
    cur.execute("""
        SELECT e.*, u.username as host_username 
        FROM elections e
        JOIN users u ON e.host_id = u.id
        WHERE e.id = %s
    """, (election_id,))
    election = cur.fetchone()
    
    if request.method == 'POST':
        vote = request.form.get('vote')
        user_id = session.get('user_id')
        
        # Check for existing vote
        cur.execute("""
            SELECT * FROM participants 
            WHERE user_id = %s AND election_id = %s
        """, (user_id, election_id))
        
        if cur.fetchone():
            flash('You have already voted in this election', 'error')
            cur.close()
            return redirect(url_for('home'))
        
        # Record the vote
        cur.execute("""
            INSERT INTO participants (user_id, election_id, vote) 
            VALUES (%s, %s, %s)
        """, (user_id, election_id, vote))
        mysql.connection.commit()
        cur.close()
        
        flash('Your vote has been recorded successfully!', 'success')
        return redirect(url_for('results', election_id=election_id))
    
    cur.close()
    return render_template('vote.html',
                         election_id=election_id,
                         election_title=election['title'],
                         host_username=election['host_username'])

# Publish Results Route
@app.route('/results/<int:election_id>')
def results(election_id):
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM participants WHERE election_id = %s", (election_id,))
    votes = cur.fetchall()
    cur.close()

    # Calculate results
    results = {}
    for vote in votes:
        if vote['vote'] in results:
            results[vote['vote']] += 1
        else:
            results[vote['vote']] = 1

    return render_template('results.html', results=results)

# Prevent Caching
@app.after_request
def after_request(response):
    # Add headers to prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    app.run(debug=True)