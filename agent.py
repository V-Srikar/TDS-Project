import os
import google.generativeai as genai
from google.generativeai.types import content_types
from collections.abc import Iterable
import tools
from dotenv import load_dotenv

load_dotenv()

# Configure API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Define the tools available to the model
available_tools = [
    tools.download_file,
    tools.read_file_content,
    tools.run_python_code,
    tools.ocr_image,
    tools.transcribe_audio,
    tools.encode_image_to_base64,
    tools.install_package
]

def get_agent_response(question: str, context: str = "") -> str:
    """
    Solves a question using the Gemini Agent with tools.
    """
    if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not set."

    # System instruction to guide the agent
    STUDENT_EMAIL = os.getenv("STUDENT_EMAIL", "unknown@example.com")
    system_instruction = f"""
    You are an expert Data Analyst and Python Programmer.
    Your goal is to solve quiz questions accurately.
    
    Your email address is: {STUDENT_EMAIL}
    If a question asks for your email or calculations based on it, use this value.
    
    You have access to the following tools:
    1. `download_file(url)`: Download files mentioned in the question.
    2. `read_file_content(path)`: Read the content of downloaded files (PDF, CSV, etc.).
    3. `run_python_code(code)`: Execute Python code to perform calculations, data analysis, or text processing.
    4. `ocr_image(path)`: Extract text from images.
    5. `transcribe_audio(path)`: Convert audio files to text.
    6. `encode_image_to_base64(path)`: Use this if the answer requires a base64 string of an image. It returns a placeholder key (BASE64_KEY:...) which you should return as the answer.
    7. `install_package(name)`: Install missing Python packages if needed for your code.
    
    STRATEGY:
    - If the question involves a file, ALWAYS download it first.
    - If the file is a PDF or CSV, read its content or summary.
    - If the file is an image and you need text, use `ocr_image`.
    - If the file is audio, use `transcribe_audio`.
    - If the question requires calculation (sum, count, average, etc.), DO NOT do it mentally. WRITE PYTHON CODE to calculate it.
    - If the question requires extracting specific data, use Python or read the file content carefully.
    - If the answer requires an image file as base64, use `encode_image_to_base64` and return the key it gives you.
    - Always double-check your logic.
    - Return the FINAL ANSWER only.
    """

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", # Use a capable model
        tools=available_tools,
        system_instruction=system_instruction
    )

    # Start a chat session
    chat = model.start_chat(enable_automatic_function_calling=True)

    # Construct the prompt
    prompt = f"""
    Context/HTML Content:
    {context}
    
    Question:
    {question}
    
    Solve this step-by-step using the tools provided.
    """

    try:
        response = chat.send_message(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error processing request: {str(e)}"
