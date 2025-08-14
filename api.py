import os
import smtplib
import random
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import mysql.connector

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# --- DATABASE & EMAIL CONFIGURATION ---
# Using the same DB credentials from your chatbot.py
DB_CONFIG = {
    'host': 'localhost',
    'user': 'aiuser',
    'password': 'aipassword',
    'database': 'ai_bot'
}

# --- FILL IN YOUR EMAIL CREDENTIALS FOR OTP ---
SMTP_SERVER = 'smtp.gmail.com'  # Example for Gmail
SMTP_PORT = 587
SENDER_EMAIL = 'amritritesh4@gmail.com'
SENDER_PASSWORD = 'xywjzqibjznxumym' # Use an "App Password" for security

# --- HELPER FUNCTIONS ---

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
        return None

def send_otp_email(recipient_email, otp):
    try:
        msg = MIMEText(f'Your TARS verification OTP is: {otp}\n\nThis code will expire in 10 minutes.')
        msg['Subject'] = 'TARS Email Verification'
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

# --- API ENDPOINTS ---

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    if not conn: return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s OR username = %s", (email, username))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': 'Email or username already exists'}), 409

    otp = str(random.randint(100000, 999999))
    otp_expiry = datetime.now() + timedelta(minutes=10)
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    if not send_otp_email(email, otp):
        cursor.close()
        conn.close()
        return jsonify({'error': 'Failed to send verification email'}), 500

    sql = "INSERT INTO users (username, email, password_hash, otp, otp_expiry, is_verified) VALUES (%s, %s, %s, %s, %s, FALSE)"
    cursor.execute(sql, (username, email, password_hash, otp, otp_expiry))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return jsonify({'message': 'Registration successful. Please check your email for an OTP.'}), 201


@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')

    if not all([email, otp]): return jsonify({'error': 'Email and OTP are required'}), 400

    conn = get_db_connection()
    if not conn: return jsonify({'error': 'Database connection failed'}), 500
        
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    if user['otp'] != otp or datetime.now() > user['otp_expiry']:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Invalid or expired OTP'}), 400

    cursor.execute("UPDATE users SET is_verified = TRUE, otp = NULL, otp_expiry = NULL WHERE email = %s", (email,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return jsonify({'message': 'Email verified successfully! You can now log in.'}), 200


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]): return jsonify({'error': 'Email and password are required'}), 400

    conn = get_db_connection()
    if not conn: return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()  # The user data is fetched into the 'user' variable
    
    cursor.close()
    conn.close()

    if not user or not bcrypt.check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user['is_verified']:
        return jsonify({'error': 'Please verify your email before logging in'}), 403

    # CORRECTED: Use the correct 'user' variable here
    return jsonify({
        "message": "Login successful", 
        "username": user['username'],
        "userId": user['id']
    })


if __name__ == '__main__':
    # Run this on a different port than your chatbot (e.g., 5001)
    app.run(host='0.0.0.0', port=5001, debug=True)
