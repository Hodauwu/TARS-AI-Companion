import os
import time
import json
import random
import shutil
import subprocess
import tempfile
import atexit
from datetime import datetime
import requests
import mysql.connector
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pydub import AudioSegment
import whisper
import configparser
# NEW: Import the Google Generative AI library
import google.generativeai as genai

# ----------------- Configuration ----------------
app = Flask(__name__)
# Using a more specific CORS configuration to allow your frontend to connect
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"])

# --- API Keys ---
TOMORROW_API_KEY = "f3ykPwS9fs7y9kCOBCxg0RNkh4tiTMKQ"
NEWS_API_KEY = "41e9704fcb334c3c92c4f4a4ea0fe14d"
RAPIDAPI_KEY = "522e952931msh333c5d80fc13c3p173272jsn34edf4898247"
GEMINI_API_KEY = "" # Your key is now here
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "aiuser",
    "password": "aipassword",
    "database": "ai_bot",
}

# --- Project Paths ---
BASE_DIR    = "/home/hodauwu/C/ai bot"
STATIC_DIR  = os.path.join(BASE_DIR, "static")
AUDIO_DIR   = os.path.join(STATIC_DIR, "audio")
PIPER_BIN   = os.path.join(BASE_DIR, "piper", "build", "piper")
PIPER_MODEL = os.path.join(BASE_DIR, "piper", "models", "TARS.onnx")
PIPER_CONF  = os.path.join(BASE_DIR, "piper", "models", "TARS.onnx.json")
TARS_JSON_PATH = os.path.join(BASE_DIR, "TARS.json")
PERSONA_INI_PATH = os.path.join(BASE_DIR, "persona.ini")

os.makedirs(AUDIO_DIR, exist_ok=True)

# --- Model Loading ---
WHISPER_MODEL = whisper.load_model("small")
# NEW: Initialize the Gemini model only if the API key is provided
GEMINI_MODEL = genai.GenerativeModel('gemini-2.5-flash') if GEMINI_API_KEY else None

# --- Temporary Directory Setup ---
temp_dir = tempfile.mkdtemp()
atexit.register(shutil.rmtree, temp_dir, ignore_errors=True)

from pydub.utils import which
AudioSegment.converter = which("ffmpeg")
AudioSegment.ffprobe = which("ffprobe")

# --- Load Persona Data ---
TARS_PERSONA_DATA = {}
try:
    with open(TARS_JSON_PATH, 'r') as f:
        TARS_PERSONA_DATA = json.load(f)
    app.logger.info("Loaded TARS.json persona data.")
except Exception as e:
    app.logger.error(f"Error loading TARS.json: {e}")

PERSONA_INI_DATA = {}
try:
    config = configparser.ConfigParser()
    config.read(PERSONA_INI_PATH)
    if 'PERSONA' in config:
        PERSONA_INI_DATA = dict(config['PERSONA'])
    app.logger.info("Loaded persona.ini data.")
except Exception as e:
    app.logger.error(f"Error parsing persona.ini: {e}")

# ----------------- Helper & Database Functions ----------------
def connect_db():
    return mysql.connector.connect(**DB_CONFIG)

# NEW: Function to check for an active internet connection
def is_online():
    """Checks if the server can connect to the internet."""
    try:
        # Use a reliable and fast endpoint for the check
        requests.get("http://1.1.1.1", timeout=3)
        app.logger.info("Internet connection detected.")
        return True
    except requests.ConnectionError:
        app.logger.warning("No internet connection detected.")
        return False

# ----------------- AI Processing ----------------

# NEW: Function to interact with the Gemini API for current affairs
def chat_with_gemini(user_input, context):
    """
    Gets a response from the Gemini API for queries requiring up-to-date information.
    """
    if not GEMINI_MODEL:
        return "My connection to the wider network seems to be down, and I can't answer that right now."

    prompt = f"""
    You are TARS, a witty AI assistant. A user is asking a question that requires up-to-date, real-world information.
    Based on the following conversation history and the user's question, provide a concise and factual answer.
    Maintain your core persona but prioritize accuracy for this specific query.

    History:
    {context}

    User Question: "{user_input}"

    Factual Answer:
    """
    try:
        response = GEMINI_MODEL.generate_content(prompt)
        # Add a natural-sounding prefix
        prefixes = ["Alright, I looked it up.", "Okay, here's what I found.", "Let's see..."]
        return f"{random.choice(prefixes)} {response.text.strip()}"
    except Exception as e:
        app.logger.error(f"Gemini API Error: {str(e)}")
        return "I'm having trouble accessing my external knowledge base for that topic. Please try again."

def generate_conversation_context(conversation_id, user_id):
    """Generates a string of the last few messages for context."""
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        # Get the last 5 exchanges (user input + AI response)
        cursor.execute("SELECT user_input, ai_response FROM chat_history WHERE conversation_id = %s AND user_id = %s ORDER BY id DESC LIMIT 5", (conversation_id, user_id))
        context_messages = cursor.fetchall()[::-1] # Reverse to get chronological order
        return "\n".join([f"User: {msg['user_input']}\nTARS: {msg['ai_response']}" for msg in context_messages])
    except Exception as e:
        app.logger.error(f"Context generation error: {str(e)}")
        return ""
    finally:
        if conn and conn.is_connected(): conn.close()

def get_weather(city):
    """Fetches weather data from Tomorrow.io."""
    # The API endpoint for real-time weather from Tomorrow.io
    url = "https://api.tomorrow.io/v4/weather/realtime"
    
    # Parameters for the API call
    params = {
        "location": city,
        "apikey": TOMORROW_API_KEY,
        "units": "metric"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # This will raise an error for bad responses (4xx or 5xx)
        data = response.json()
        
        # Extract the temperature and humidity from the response
        temp = data["data"]["values"]["temperature"]
        humidity = data["data"]["values"]["humidity"]
        
        return f"According to Tomorrow.io, the current weather in {city} is {temp}°C with humidity at {humidity}%."

    except requests.exceptions.HTTPError as http_err:
        # Handle cases where the city might not be found (404) or other API errors
        app.logger.error(f"Tomorrow.io HTTP Error: {http_err} - {response.text}")
        return "I couldn't fetch the weather for that location. Please check the city name."
    except Exception as e:
        # Handle other errors like network issues
        app.logger.error(f"Tomorrow.io API Error: {str(e)}")
        return "Oops! I ran into an issue while fetching the weather."
    
def get_latest_news(topic=None):
    """Fetches top headlines from NewsAPI, optionally on a specific topic."""
    if topic:
        url = "https://newsapi.org/v2/everything"
        params = {'q': topic, 'apiKey': NEWS_API_KEY, 'pageSize': 3, 'language': 'en'}
    else:
        # Fetch top headlines from India since you are located there
        url = "https://newsapi.org/v2/top-headlines"
        params = {'country': 'in', 'apiKey': NEWS_API_KEY, 'pageSize': 3}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "ok" and data.get("articles"):
            articles = data["articles"]
            # Format the headlines into a clean, readable string
            headlines = [f"{i+1}. {article['title']} (Source: {article['source']['name']})" for i, article in enumerate(articles)]
            response_text = "Alright, here are the top headlines I found:\n" + "\n".join(headlines)
            return response_text
        else:
            return "I couldn't find any news articles right now. Please try again later."

    except Exception as e:
        app.logger.error(f"NewsAPI Error: {str(e)}")
        return "Sorry, I ran into an issue while trying to fetch the latest news."
    
def get_india_current_affairs():
    """Fetches recent current affairs from the RapidAPI service."""
    url = "https://current-affairs-of-india.p.rapidapi.com/recent"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "current-affairs-of-india.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # NOTE: The structure of 'data' is unknown. We assume it's a list of objects.
        # You may need to print(data) first and adjust the parsing below.
        if data:
            # Assuming each item in the list is a dictionary with a 'news' key.
            # You might need to change 'news' to 'title', 'headline', etc.
            affairs = [f"- {item.get('news', 'No title available')}" for item in data[:5]] # Get top 5
            return "Here are the latest current affairs for India:\n" + "\n".join(affairs)
        else:
            return "I couldn't find any recent current affairs at the moment."

    except Exception as e:
        app.logger.error(f"Current Affairs API Error: {str(e)}")
        return "Sorry, I had trouble fetching the current affairs information."
    
def get_today_in_history():
    """Fetches historical events for today from the RapidAPI service."""
    url = "https://current-affairs-of-india.p.rapidapi.com/history-of-today"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "current-affairs-of-india.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # NOTE: Adjust the parsing based on the actual response from the API.
        if data:
            # Assuming the response has a key 'data' which is a list of events.
            events = [f"- {event}" for event in data.get('data', [])[:5]] # Get top 5 events
            return "Here is what happened today in history:\n" + "\n".join(events)
        else:
            return "I couldn't find any historical events for today."

    except Exception as e:
        app.logger.error(f"Today in History API Error: {str(e)}")
        return "Sorry, I had trouble fetching today's history."

def chat_with_local_ai(user_input, context, humor_intensity=50):
    """Generates a response using the local Ollama model for conversational chat."""
    char_persona = TARS_PERSONA_DATA.get("char_persona", "A witty, fast-thinking AI.")
    world_scenario = TARS_PERSONA_DATA.get("world_scenario", "Advanced AI assistant.")
    ini_traits_str = "\n".join([f"- {k.replace('_', ' ').capitalize()}: {v}" for k, v in PERSONA_INI_DATA.items()])

    if humor_intensity >= 75:
        extra_instructions = "You have MAXIMUM humor. Use witty sarcasm and clever wordplay."
    elif humor_intensity >= 50:
        extra_instructions = "Your humor is MODERATE. Include jokes and wordplay."
    else:
        extra_instructions = "You are straightforward, with minimal jokes."               

    """
    Determines whether to use a specific function (news, weather) or an AI model.
    """
    # --- 1. Check for specific commands first ---
    lower_input = user_input.lower()

    if "time" in lower_input:
        return f"Let me check... Right now, it's {get_current_time()}."

    if "weather" in lower_input or "temperature" in lower_input:
        words = lower_input.split()
        for i in range(len(words) - 1):
            if words[i] == "in":
                return get_weather(words[i + 1])
        return "Can you specify a city? For example: 'What's the weather in London?'"
    
    if "news" in lower_input and not "current affairs" in lower_input: # Avoid conflict with below
        topic = None
        if "about" in lower_input:
            topic = lower_input.split("about", 1)[1].strip()
        elif "on" in lower_input:
            topic = lower_input.split("on", 1)[1].strip()
        return get_latest_news(topic)

    # NEW: Check for Current Affairs of India
    if "current affairs" in lower_input:
        return get_india_current_affairs()

    # NEW: Check for Today in History
    if "today in history" in lower_input:
        return get_today_in_history()
    
    full_prompt_for_ollama = f"""{get_current_time()}
You are TARS.
Persona: {char_persona}
Scenario: {world_scenario}
Core Personality Traits:
{ini_traits_str}
STRICT RULES:
- NEVER use asterisks * or parentheses ().
- NEVER describe actions like *pausing, smiling, thinking*.
- ONLY use natural spoken phrases like 'uhh', 'hmm', or 'let me think...'.
- Your humor intensity is {humor_intensity}/100. {extra_instructions}
{context}
User: {user_input}
TARS:"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tars-llama3.1-4km",
                "prompt": full_prompt_for_ollama,
                "stream": False,
                "options": {"temperature": 0.6, "num_predict": 150, "stop": ["\nUser:", "\nTARS:", "\n"]}
            }
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception as e:
        app.logger.error(f"Ollama Error: {str(e)}")
        return "I seem to be having a local processing issue right now."


# NEW: Master function to decide which AI model to use
# NEW: Master function to decide which AI model to use
def chat_with_ai(user_input, conversation_id, user_id, humor_intensity):
    """
    Determines whether to use the Gemini API (for current affairs) or the local model.
    """
    # First, handle simple, hardcoded commands
    if "time" in user_input.lower():
        return f"Let me check... Right now, it's {get_current_time()}."
    if "weather" in user_input.lower() or "temperature" in user_input.lower():
        words = user_input.split()
        for i in range(len(words) - 1):
            if words[i].lower() == "in":
                return get_weather(words[i + 1])
        return "Can you specify a city? For example: 'What's the weather in London?'"

    context = generate_conversation_context(conversation_id, user_id)

    # Keywords that suggest a need for real-time, external information
    current_affairs_keywords = [
        'who is', 'who was', 'what is the latest', 'news about', 'what happened to',
        'stock price of', 'election results', 'recent movie', 'new song by',
        'latest update on', 'define', 'explain', 'tell me about', 'what are',
        'history of', 'how does'
    ]

    # --- THE FIX IS HERE ---
    # Changed from startswith(keyword) to keyword in user_input.lower()
    is_current_affairs_query = any(keyword in user_input.lower() for keyword in current_affairs_keywords)

    # Route to Gemini if the query is for current affairs AND we are online
    if GEMINI_MODEL and is_current_affairs_query and is_online():
        app.logger.info(">>> Query identified as current affairs. Routing to Gemini API.")
        return chat_with_gemini(user_input, context)
    else:
        # Otherwise, use the local model for general chat or if offline
        app.logger.info(">>> Query is general or offline. Routing to local Ollama model.")
        return chat_with_local_ai(user_input, context, humor_intensity)


# ----------------- Audio & Main Endpoints ----------------
def synthesize_speech(text, pitch=None, speed=None):
    """Converts text to speech using Piper and returns the filename."""
    temp_wav = os.path.join(BASE_DIR, "tts_temp.wav")
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
    filename  = f"speech_{int(time.time())}.wav"
    final_wav = os.path.join(AUDIO_DIR, filename)
    cmd = [PIPER_BIN, "--model", PIPER_MODEL, "--config", PIPER_CONF, "--output_file", temp_wav]
    if pitch is not None: cmd += ["-p", str(pitch)]
    if speed is not None: cmd += ["-s", str(speed)]
    try:
        subprocess.run(cmd, input=text, text=True, capture_output=True, check=True)
        if os.path.exists(temp_wav):
            shutil.move(temp_wav, final_wav)
            return filename
    except subprocess.CalledProcessError as e:
        app.logger.error("Piper failed: stdout=%s stderr=%s", e.stdout, e.stderr)
    return None

@app.route("/chat", methods=["POST"])
def handle_chat():
    """Main endpoint for handling user chat messages."""
    data = request.get_json(force=True)
    user_input = data.get("message", "").strip()
    conversation_id = data.get("conversation_id")
    user_id = data.get("user_id")
    humor_intensity = data.get("humor_intensity", 50)

    if not all([user_input, conversation_id, user_id]):
        return jsonify({"error": "Missing required fields"}), 400

    ai_response = "An error occurred while getting a response."
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Verify that the user owns the conversation
        cursor.execute("SELECT id FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, user_id))
        if not cursor.fetchone(): return jsonify({"error": "Forbidden or conversation not found"}), 403

        # NEW: Get the AI response from the new master AI function
        ai_response = chat_with_ai(user_input, conversation_id, user_id, humor_intensity)

        # Save the interaction to the database
        cursor.execute("INSERT INTO chat_history (conversation_id, user_id, user_input, ai_response) VALUES (%s, %s, %s, %s)", (conversation_id, user_id, user_input, ai_response))
        conn.commit()
    except Exception as e:
        app.logger.error("DB write/check or AI call failed: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected(): conn.close()

    # Synthesize the AI response to audio
    filename = synthesize_speech(ai_response, data.get("pitch"), data.get("speed"))
    return jsonify({"text": ai_response, "audio_url": f"/static/audio/{filename}" if filename else None})


@app.route("/conversations", methods=["GET", "POST"])
def handle_conversations():
    if request.method == "GET":
        user_id = request.args.get("user_id")
        if not user_id: return jsonify({"error": "user_id is required"}), 400
        try:
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT c.id, c.created_at, c.title, c.user_id,
                (SELECT ch.user_input FROM chat_history ch WHERE ch.conversation_id = c.id ORDER BY ch.id ASC LIMIT 1) as first_message
                FROM conversations c WHERE c.user_id = %s ORDER BY c.created_at DESC
            """, (user_id,))
            conversations = cursor.fetchall()
            for conv in conversations:
                if not conv['title'] and conv['first_message']:
                    conv['title'] = conv['first_message'][:50] + ("..." if len(conv['first_message']) > 50 else "")
            return jsonify(conversations)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if conn and conn.is_connected(): conn.close()

    elif request.method == "POST":
        user_id = request.json.get("user_id")
        if not user_id: return jsonify({"error": "user_id is required"}), 400
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO conversations (user_id, created_at) VALUES (%s, NOW())", (user_id,))
            conn.commit()
            return jsonify({"id": cursor.lastrowid, "user_id": user_id}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if conn and conn.is_connected(): conn.close()


@app.route("/conversations/<int:conversation_id>", methods=["GET", "PATCH", "DELETE"])
def handle_conversation(conversation_id):
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        user_id = request.args.get('user_id') if request.method == "GET" else request.json.get('user_id')
        if not user_id: return jsonify({"error": "user_id is required"}), 400

        cursor.execute("SELECT user_id FROM conversations WHERE id = %s", (conversation_id,))
        conversation = cursor.fetchone()
        if not conversation or conversation['user_id'] != int(user_id):
            return jsonify({"error": "Forbidden or conversation not found"}), 403

        if request.method == "GET":
            cursor.execute("""
                SELECT user_input as text, 'user' as sender, created_at FROM chat_history WHERE conversation_id = %s
                UNION ALL
                SELECT ai_response as text, 'bot' as sender, created_at FROM chat_history WHERE conversation_id = %s
                ORDER BY created_at ASC
            """, (conversation_id, conversation_id))
            return jsonify({"messages": cursor.fetchall()})

        elif request.method == "PATCH":
            new_title = request.json.get("title", "").strip()
            if not new_title: return jsonify({"error": "Empty title"}), 400
            cursor.execute("UPDATE conversations SET title = %s WHERE id = %s", (new_title, conversation_id))
            conn.commit()
            return jsonify({"success": True})

        elif request.method == "DELETE":
            cursor.execute("DELETE FROM chat_history WHERE conversation_id = %s", (conversation_id,))
            cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected(): conn.close()

@app.route("/transcribe", methods=["POST"])
def handle_transcription():
    if "audio" not in request.files: return jsonify({"error": "No audio file provided"}), 400
    audio_file = request.files["audio"]
    temp_path = os.path.join(temp_dir, f"recording_{int(time.time()*1000)}.webm")
    audio_file.save(temp_path)
    try:
        audio = AudioSegment.from_file(temp_path, format="webm")
        wav_temp_path = os.path.join(temp_dir, f"recording_converted_{int(time.time()*1000)}.wav")
        audio.export(wav_temp_path, format="wav", parameters=["-ac", "1", "-ar", "16000"])
        result = WHISPER_MODEL.transcribe(wav_temp_path)
        return jsonify({"text": result.get("text", "").strip()})
    except Exception as e:
        app.logger.error(f"Transcription error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)
        if 'wav_temp_path' in locals() and os.path.exists(wav_temp_path): os.remove(wav_temp_path)


@app.route("/detect_wake_word", methods=["POST"])
def detect_wake_word():
    # This endpoint seems fine and doesn't need changes for Gemini integration.
    # It can remain as is.
    if "audio" not in request.files: return jsonify({"error": "No audio file provided"}), 400
    audio_file = request.files["audio"]
    temp_path = os.path.join(temp_dir, f"wake_word_rec_{int(time.time()*1000)}.webm")
    audio_file.save(temp_path)
    wake_word_detected = False
    try:
        audio = AudioSegment.from_file(temp_path, format="webm")
        wav_temp_path = os.path.join(temp_dir, f"wake_word_rec_converted_{int(time.time()*1000)}.wav")
        audio.export(wav_temp_path, format="wav", parameters=["-ac", "1", "-ar", "16000"])
        result = WHISPER_MODEL.transcribe(wav_temp_path, fp16=False) # fp16=False can improve stability
        transcribed_text = result.get("text", "").strip().lower()
        wake_phrases = ["hey tars", "hi tars", "tars", "hey stars", "hey darns", "hey tarz", "hey dars"]
        if any(phrase in transcribed_text for phrase in wake_phrases):
            wake_word_detected = True
    except Exception as e:
        app.logger.error(f"Wake word detection error: {str(e)}")
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)
        if 'wav_temp_path' in locals() and os.path.exists(wav_temp_path): os.remove(wav_temp_path)
    return jsonify({"wake_word_detected": wake_word_detected})

def get_current_time():
    return time.strftime("%I:%M %p on %B %d, %Y")

@app.route("/static/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000, debug=True)
