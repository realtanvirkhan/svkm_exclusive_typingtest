from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import sqlite3
import secrets
from database import initialize_database

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key

# Initialize database on startup
initialize_database()

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('svkm_typing.db')
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    action = request.form.get('action')
    email = request.form.get('email')
    sap_id = request.form.get('sap-id')  # This matches the form field name exactly

    # Print debug information
    print("Form data received:", request.form)
    print("Action:", action)
    print("Email:", email)
    print("SAP ID:", sap_id)

    if not email or not sap_id:
        error_msg = "Email and SAP ID are required."
        print("Error:", error_msg)
        return render_template('login.html', error=error_msg)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if action == 'signup':
            name = request.form.get('name')
            college = request.form.get('college')
            
            if not name or not college:
                return "Name and College are required for signup.", 400
            
            # Check if user already exists
            cursor.execute('SELECT * FROM users WHERE email = ? OR sap_id = ?', (email, sap_id))
            existing_user = cursor.fetchone()
            
            if existing_user:
                error_msg = "User already exists with this email or SAP ID."
                print("Error:", error_msg)
                return render_template('login.html', error=error_msg)
            
            # Insert new user
            cursor.execute('''INSERT INTO users (name, email, sap_id, college) 
                            VALUES (?, ?, ?, ?)''', (name, email, sap_id, college))
            conn.commit()
            
        elif action == 'login':
            # Verify user credentials
            cursor.execute('SELECT * FROM users WHERE email = ? AND sap_id = ?', (email, sap_id))
            user = cursor.fetchone()
            
            if not user:
                error_msg = "Invalid credentials. Please try again."
                print("Error:", error_msg)
                return render_template('login.html', error=error_msg)
        
        else:
            error_msg = "Invalid action specified."
            print("Error:", error_msg)
            return render_template('login.html', error=error_msg)

    except sqlite3.Error as e:
        return f"Database error: {str(e)}", 500
    finally:
        conn.close()

    # If we get here, either login or signup was successful
    # Store user info in session
    session['user'] = {
        'email': email,
        'sap_id': sap_id
    }
    return redirect(url_for('main'))

@app.route('/main')
@app.route('/home')
def main():
    print("Session data:", session)
    if 'user' not in session:
        print("No user in session, redirecting to login")
        return redirect(url_for('login'))
    print("User found in session, rendering main.html")
    return render_template('main.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/submit_result', methods=['POST'])
def submit_result():
    data = request.json
    email = data.get('email')
    wpm = data.get('wpm')
    accuracy = data.get('accuracy')
    raw_wpm = data.get('raw_wpm')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get user_id from email
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})

        # Insert test result
        cursor.execute('''
            INSERT INTO test_results (user_id, wpm, accuracy, raw_wpm)
            VALUES (?, ?, ?, ?)
        ''', (user['id'], wpm, accuracy, raw_wpm))
        conn.commit()
        return jsonify({'success': True})

    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

@app.route('/leaderboard')
def leaderboard():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    college = request.args.get('college', 'all')
    rankings = []
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # First check if there are any users
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]

        if user_count == 0:
            return render_template('leaderboard.html', rankings=[], selected_college=college)

        if college != 'all':
            # Get college-specific leaderboard
            cursor.execute('''
                SELECT 
                    u.name,
                    u.college,
                    COALESCE(MAX(t.wpm), 0) as best_wpm,
                    COALESCE(AVG(t.accuracy), 0) as avg_accuracy,
                    COUNT(t.id) as tests_taken
                FROM users u
                LEFT JOIN test_results t ON u.id = t.user_id
                WHERE u.college = ?
                GROUP BY u.id, u.name, u.college
                ORDER BY best_wpm DESC
            ''', (college,))
        else:
            # Get global leaderboard
            cursor.execute('''
                SELECT 
                    u.name,
                    u.college,
                    COALESCE(MAX(t.wpm), 0) as best_wpm,
                    COALESCE(AVG(t.accuracy), 0) as avg_accuracy,
                    COUNT(t.id) as tests_taken
                FROM users u
                LEFT JOIN test_results t ON u.id = t.user_id
                GROUP BY u.id, u.name, u.college
                ORDER BY best_wpm DESC
            ''')
        
        rankings = cursor.fetchall()
        return render_template('leaderboard.html', rankings=rankings, selected_college=college)
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return render_template('leaderboard.html', rankings=[], selected_college=college)
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/about')
def about():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('about.html')

@app.route('/contact')
def contact():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('contact.html')

@app.route('/get_user_info')
def get_user_info():
    if 'user' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Email required'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT name, email, college, sap_id FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if user:
            return jsonify({
                'name': user['name'],
                'email': user['email'],
                'college': user['college'],
                'sapId': user['sap_id']
            })
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)