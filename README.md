TARS.ai: A Voice-First AI Companion
TARS.ai is a multi-user, voice-first AI companion with a unique, retro-inspired personality. It's designed to provide a natural and engaging conversational experience, moving beyond a simple chatbot to become a personalized AI buddy. The entire system is built on a stack of modern web technologies and self-hosted, open-source AI models.


Core Features
Cinematic Homepage: A scroll-animated landing page (built with GSAP) introduces users to the TARS aesthetic.

Secure Multi-User System: Full user registration with email OTP verification and secure login. Each user has a private and persistent conversation history.

Voice-First Interface: The primary interaction mode is through voice, featuring real-time speech-to-text.

Expressive AI Persona: TARS has an animated face that provides visual feedback for listening, thinking, speaking, and emotional states (like joking or error).

Customizable Personality: Users can adjust the AI's humor intensity, which directly influences the tone and content of its responses.

Dual Interaction Modes: Seamlessly switch between the immersive voice-first view and a traditional text-based chat log.

Self-Hosted AI Stack: All AI functionalities run locally, ensuring privacy and control.

Technology Stack
Frontend
Framework: React (with Vite)

Styling: Tailwind CSS

Animation: GSAP (GreenSock Animation Platform) for scroll-telling.

UI Components: lucide-react for icons.

Backend
Framework: Python with Flask (two separate microservices for Auth and Chat).

Database: MySQL

Authentication: Bcrypt for password hashing.

AI & Machine Learning
Large Language Model: Ollama running Llama 3.1 (tars-llama3.1-4km).

Text-to-Speech (TTS): Piper TTS for generating a custom, real-time voice.

Speech-to-Text (STT): OpenAI Whisper (small model) for accurate transcription.

Local Setup & Installation
Prerequisites:

Node.js and npm

Python 3.x and pip

MySQL Server

Ollama installed and running

1. Clone the repository:

git clone https://github.com/YourUsername/TARS-AI-Companion.git
cd TARS-AI-Companion

2. Backend Setup:

# Navigate to the root directory
cd "/path/to/TARS-AI-Companion"

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate


# Setup the database using the provided .sql files
# Run the authentication and chatbot servers
python3 api.py
python3 chatbot.py

3. Frontend Setup:

# Navigate to the frontend directory
cd ai-bot-web

# Install Node.js dependencies
npm install

# Start the React development server
npm run dev

The homepage will be available at http://localhost:8000 and the chat app at http://localhost:5173.
