from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import mysql.connector

app = Flask(__name__)
CORS(app)  # Allows frontend to access backend

# Connect to MySQL Database
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="aramrit1",  # Change this to your MySQL password
        database="ai_bot"
    )

# Handle chat messages
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "No message received"}), 400

    # Call Local AI (KoboldCpp) for response
    url = "http://localhost:5001/api/v1/generate"
    payload = {
        "prompt": f"User: {user_message}\nAI:",
        "max_length": 100,
        "temperature": 1.0
    }
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        ai_response = response.json().get("results", [{}])[0].get("text", "").strip()
    else:
        ai_response = "Error in AI response"

    # Save conversation in database
    try:
        conn = connect_db()
        cursor = conn.cursor()
        query = "INSERT INTO chat_history (user_input, ai_response) VALUES (%s, %s)"
        cursor.execute(query, (user_message, ai_response))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Database Error:", str(e))

    return jsonify({"response": ai_response})

# Run the Flask server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
