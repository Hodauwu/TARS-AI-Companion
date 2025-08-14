import os
import subprocess

# Define paths
PIPER_PATH = r"C:\ai bot\piper\piper.exe"
MODEL_PATH = r"C:\ai bot\piper\TARS.onnx"
OUTPUT_DIR = r"C:\ai bot\TARS_dataset\wavs"
METADATA_FILE = r"C:\ai bot\TARS_dataset\metadata\metadata.csv"

# List of phrases to generate
phrases = [
    "Hello, I am TARS. How can I assist you?",
    "The current weather is 25 degrees Celsius with clear skies.",
    "I'm designed for mission-critical operations.",
    "This conversation will be logged for future reference.",
    "My humor settings are adaptive. Want a joke?",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(METADATA_FILE, "w", encoding="utf-8") as f:
    for i, text in enumerate(phrases):
        audio_file = f"tars_{i}.wav"
        output_path = os.path.join(OUTPUT_DIR, audio_file)
        
        # Run Piper command
        command = [
            PIPER_PATH,
            "-m", MODEL_PATH,
            "-o", output_path,
            "-t", text
        ]
        subprocess.run(command, check=True)

        # Write metadata
        f.write(f"{audio_file}|{text}\n")

print("✅ Dataset generated successfully!")
