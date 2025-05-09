from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1972'
app.config['MYSQL_DB'] = 'project1'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)
app.secret_key = 'your_secret_key_here'

@app.route('/')
def loginpage():
    return render_template('login.html')

@app.route('/home')
def home():
    if not session.get('logged_in'): 
        return redirect(url_for('loginpage'))
    username = session.get('username')              #gets username from the session to display in the navbar
    return render_template('index.html', username=username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        cur = mysql.connection.cursor()
        
        try:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))  #checks whether the user with the username is present
            user = cur.fetchone()
            
            if user and user['password'] == password:  #if present
                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = user['id']
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
        finally:
            cur.close()
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        mail = request.form.get('email')
        cur = mysql.connection.cursor()

        try:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                flash('Username already exists', 'error')
                return redirect(url_for('register'))
            
            cur.execute("INSERT INTO users (username, password, mail) VALUES (%s, %s, %s)", 
                       (username, password, mail))
            mysql.connection.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('loginpage'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Registration error: {str(e)}', 'error')
        finally:
            cur.close()

    return render_template('registration.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('loginpage'))

@app.route('/host')
def host():
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    user_id = session.get('user_id')
    cur = mysql.connection.cursor()
    
    try:#selects all the election under the user_id of the user
        cur.execute("""
            SELECT id, title, password, results_published 
            FROM elections 
            WHERE host_id = %s
        """, (user_id,))
        
        elections = cur.fetchall()
        return render_template('host.html', elections=elections)
    except Exception as e:
        flash(f'Error retrieving elections: {str(e)}', 'error')
        return redirect(url_for('home'))
    finally:
        cur.close()

@app.route('/create_election', methods=['GET', 'POST'])
def create_election():
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    if request.method == 'POST':
        user_id = session.get('user_id')
        title = request.form.get('title')
        password = request.form.get('password')
        
        cur = mysql.connection.cursor()
        try:
            #checking if the password exist
            cur.execute("""
                SELECT id FROM elections 
                WHERE password = %s 
            """, (password,))
            existing_election = cur.fetchone()
            
            if existing_election:
                flash('This password is unavailable', 'error')
                return render_template('create_election.html')
            
            # Get candidate data
            candidates = [
                request.form.get('candidate1'),
                request.form.get('candidate2'),
                request.form.get('candidate3'),
                request.form.get('candidate4')
            ]
            
            # Create new election and add to elections table
            cur.execute("""
                INSERT INTO elections (title, password, host_id) 
                VALUES (%s, %s, %s)
            """, (title, password, user_id))
            election_id = cur.lastrowid
            
            # Add candidates to candidate_detail table
            for candidate in candidates:
                if candidate:
                    cur.execute("""
                        INSERT INTO candidate_details (election_id, candidate_name, votes) 
                        VALUES (%s, %s, 0)
                    """, (election_id, candidate))
            
            mysql.connection.commit()
            flash('Election created successfully!', 'success')
            return redirect(url_for('host'))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error creating election: {str(e)}', 'error')
        finally:
            cur.close()

    return render_template('create_election.html')

@app.route('/participate', methods=['GET', 'POST'])
def participate():
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        cur = mysql.connection.cursor()
        
        try:#get details about the elections with the given password
            cur.execute("""
                SELECT e.id, e.title, e.results_published, u.username as host_username 
                FROM elections e
                JOIN users u ON e.host_id = u.id
                WHERE e.password = %s 
            """, (password,))
            election = cur.fetchone()
            #there are 3 checks to be passed for us to vote in election
            if election:  # First check if election exists
                if election['results_published'] == 1:  # Then check results
                    return redirect(url_for('results', election_id=election['id']))
                #if result published exist 
                # check if  voted
                cur.execute("""
                    SELECT * FROM participants 
                    WHERE user_id = %s AND election_id = %s 
                """, (session['user_id'], election['id']))
                #if already voted show
                if cur.fetchone():
                    flash('You have already voted in this election', 'warning')
                    return redirect(url_for('results', election_id=election['id']))
                # if not voted dispplay the voting page
                cur.execute("""
                    SELECT id, candidate_name 
                    FROM candidate_details 
                    WHERE election_id = %s
                """, (election['id'],))
                candidates = cur.fetchall()
                
                return render_template('vote.html', 
                                    election_id=election['id'],
                                    election_title=election['title'],
                                    host_username=election['host_username'],
                                    candidates=candidates)
            else:
                flash('Invalid election password', 'error')
                
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        finally:
            cur.close()
    
    return render_template('participate.html')

@app.route('/vote/<int:election_id>', methods=['GET', 'POST'])
def vote(election_id):
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    cur = mysql.connection.cursor()
    
    try:
        cur.execute("""
            SELECT e.title, u.username as host_username 
            FROM elections e
            JOIN users u ON e.host_id = u.id
            WHERE e.id = %s
        """, (election_id,))
        election = cur.fetchone()
        
        if not election:
            flash('Election not found', 'error')
            return redirect(url_for('home'))
        
        cur.execute("""
            SELECT id, candidate_name 
            FROM candidate_details 
            WHERE election_id = %s
        """, (election_id,))
        candidates = cur.fetchall()
        
        if request.method == 'POST':
            candidate_id = request.form.get('candidate_id')
            user_id = session.get('user_id')
            
            cur.execute("""
                SELECT * FROM participants 
                WHERE user_id = %s AND election_id = %s
            """, (user_id, election_id))
            
            if cur.fetchone():
                flash('You have already voted in this election', 'error')
                return redirect(url_for('home'))
            
            try:
                cur.execute("""
                    INSERT INTO participants (user_id, election_id, candidate_id) 
                    VALUES (%s, %s, %s)
                """, (user_id, election_id, candidate_id))
                
                cur.execute("""
                    UPDATE candidate_details 
                    SET votes = votes + 1 
                    WHERE id = %s
                """, (candidate_id,))
                
                mysql.connection.commit()
                flash('Vote recorded successfully!', 'success')
                return redirect(url_for('results', election_id=election_id))
            except Exception as e:
                mysql.connection.rollback()
                flash(f'Error recording vote: {str(e)}', 'error')
        
        return render_template('vote.html',
                            election_id=election_id,
                            election_title=election['title'],
                            host_username=election['host_username'],
                            candidates=candidates)
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('home'))
    finally:
        cur.close()

@app.route('/results/<int:election_id>')
def results(election_id):
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    cur = mysql.connection.cursor()
    
    try:
        # Get basic election info
        cur.execute("""
            SELECT e.title, e.results_published, u.username as host_name
            FROM elections e
            JOIN users u ON e.host_id = u.id
            WHERE e.id = %s
        """, (election_id,))
        election = cur.fetchone()
        
        if not election:
            flash('Election not found', 'error')
            return redirect(url_for('home'))
            
        if not election['results_published']:
            flash('Results are not yet published', 'info')
            return redirect(url_for('results_pending', election_id=election_id))
        
        # Get official results from results table
        cur.execute("""
            SELECT winner, winner_votes, total_votes, published_at
            FROM results
            WHERE election_id = %s
            ORDER BY published_at DESC
            LIMIT 1
        """, (election_id,))
        result = cur.fetchone()
        
        if not result:
            flash('No results available for this election', 'error')
            return redirect(url_for('home'))
        
        # Calculate percentage
        percentage = round((result['winner_votes'] / result['total_votes']) * 100, 2) if result['total_votes'] > 0 else 0
        
        return render_template('results.html',
                           election_title=election['title'],
                           host_name=election['host_name'],
                           winner=result['winner'],
                           winner_votes=result['winner_votes'],
                           total_votes=result['total_votes'],
                           percentage=percentage,
                           published_at=result['published_at'])
    
    except Exception as e:
        flash(f'Error retrieving results: {str(e)}', 'error')
        return redirect(url_for('home'))
    finally:
        cur.close()

@app.route('/publish_results/<int:election_id>')
def publish_results(election_id):
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    cur = mysql.connection.cursor()
    
    try:
        # Verify user is the election host
        cur.execute("SELECT host_id FROM elections WHERE id = %s", (election_id,))
        election = cur.fetchone()
        
        if not election or election['host_id'] != session['user_id']:
            flash('Unauthorized action', 'error')
            return redirect(url_for('host'))
        
        # Get the winning candidate
        cur.execute("""
            SELECT cd.id, cd.candidate_name, cd.votes
            FROM candidate_details cd
            WHERE cd.election_id = %s
            ORDER BY cd.votes DESC
            LIMIT 1
        """, (election_id,))
        winner = cur.fetchone()
        
        if not winner:
            flash('No candidates found for this election', 'error')
            return redirect(url_for('host'))
        
        # Calculate total votes
        cur.execute("""
            SELECT SUM(votes) as total_votes
            FROM candidate_details
            WHERE election_id = %s
        """, (election_id,))
        total_votes = cur.fetchone()['total_votes'] or 0
        
        # Store results in the results table
        cur.execute("""
            INSERT INTO results 
            (election_id, winner, winner_votes, total_votes)
            VALUES (%s, %s, %s, %s)
        """, (
            election_id,
            winner['candidate_name'],
            winner['votes'],
            total_votes
        ))
        
        # Mark election as published
        cur.execute("""
            UPDATE elections 
            SET results_published = TRUE 
            WHERE id = %s
        """, (election_id,))
        
        mysql.connection.commit()
        flash('Results published successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error publishing results: {str(e)}', 'error')
    finally:
        cur.close()
    
    return redirect(url_for('host'))
@app.route('/check_results', methods=['POST'])
def check_results():
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    election_password = request.form.get('election_password')
    if not election_password:
        flash('Please enter an election password', 'error')
        return redirect(url_for('home'))
    
    cur = mysql.connection.cursor()
    
    try:
        # 1. Find election by password
        cur.execute("""
            SELECT id, title, results_published 
            FROM elections 
            WHERE password = %s
        """, (election_password,))
        election = cur.fetchone()
        
        if not election:
            flash('No election found with that password', 'error')
            return redirect(url_for('home'))
            
        # 2. Check if results are published
        if election['results_published']:

            return redirect(url_for('results', election_id=election['id']))
        else:
            flash('Results are not yet published by the host', 'info')
            return redirect(url_for('results_pending', election_id=election['id']))
    
    except Exception as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('home'))
    finally:
        cur.close()
@app.route('/results_pending/<int:election_id>')
def results_pending(election_id):
    if not session.get('logged_in'):
        return redirect(url_for('loginpage'))
    
    cur = mysql.connection.cursor()
    
    try:
        cur.execute("SELECT title FROM elections WHERE id = %s", (election_id,))
        election = cur.fetchone()
        
        if not election:
            flash('Election not found', 'error')
            return redirect(url_for('home'))
        
        return render_template('results_pending.html', 
                            election_title=election['title'])
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('home'))
    finally:
        cur.close()

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    app.run(debug=True)