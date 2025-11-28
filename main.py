import os
import json
import requests
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from playwright.async_api import async_playwright
import google.generativeai as genai
from agent import get_agent_response
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
STUDENT_EMAIL = os.getenv("STUDENT_EMAIL")
STUDENT_SECRET = os.getenv("STUDENT_SECRET")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------
class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------
async def fetch_html(url: str) -> str:
    """Fetches HTML content using Playwright (Async)."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("networkidle") # Wait for JS to finish
        content = await page.content()
        await browser.close()
        return content

def extract_quiz_data(html: str):
    """Extracts the question and submit URL from the HTML using Gemini."""
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = """
    Analyze the following HTML page. It contains a quiz question and a submission URL.
    Extract the following strictly in JSON format:
    {
        "question": "The full text of the question",
        "submit_url": "The URL to submit the answer to (look for fetch/post code)",
        "required_files": ["list", "of", "file", "urls", "mentioned"]
    }
    
    HTML Content:
    """
    try:
        response = model.generate_content(prompt + html[:15000]) # Truncate if too long
        text = response.text
        # Clean up json markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return None

def submit_answer(submit_url: str, answer: any, original_url: str):
    """Submits the answer to the quiz endpoint."""
    payload = {
        "email": STUDENT_EMAIL,
        "secret": STUDENT_SECRET,
        "url": original_url,
        "answer": answer
    }
    print(f"Submitting to {submit_url}: {payload}")
    try:
        resp = requests.post(submit_url, json=payload, timeout=10)
        return resp.json()
    except Exception as e:
        return {"correct": False, "error": str(e)}

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------
async def solve_quiz_loop(start_url: str):
    """
    Recursively solves the quiz until finished.
    """
    current_url = start_url
    visited = set()

    while current_url:
        if current_url in visited:
            print(f"Loop detected: {current_url}")
            break
        visited.add(current_url)

        print(f"\n--- Processing: {current_url} ---")
        
        # 1. Fetch Page
        try:
            html = await fetch_html(current_url)
        except Exception as e:
            print(f"Failed to fetch {current_url}: {e}")
            break

        # 2. Parse Question
        data = extract_quiz_data(html)
        if not data:
            print("Failed to extract quiz data.")
            break
        
        question = data.get("question")
        submit_url = data.get("submit_url")
        
        if not question or not submit_url:
            print("Missing question or submit_url.")
            break

        print(f"Question: {question}")

        # 3. Solve Question (Agent)
        # We pass the question and the HTML context (for file links etc)
        answer_str = get_agent_response(question, context=html[:5000])
        
        # Check for Base64 Placeholder
        from tools import BASE64_STORE
        if isinstance(answer_str, str) and "BASE64_KEY:" in answer_str:
            key = answer_str.strip()
            # Extract key if it's embedded in text (simple heuristic)
            if "BASE64_KEY:" in key and key not in BASE64_STORE:
                 # Try to find the key in the string
                 import re
                 match = re.search(r"BASE64_KEY:[0-9a-f-]+", key)
                 if match:
                     key = match.group(0)

            if key in BASE64_STORE:
                print(f"Swapping placeholder {key} with actual Base64 data.")
                answer = BASE64_STORE[key]
            else:
                answer = answer_str # Fallback
        else:
            # Try to parse answer if it looks like JSON or number
            try:
                # Heuristic to clean up answer
                if answer_str.lower() == "true": answer = True
                elif answer_str.lower() == "false": answer = False
                elif answer_str.replace('.','',1).isdigit(): answer = float(answer_str) if '.' in answer_str else int(answer_str)
                else: answer = answer_str
            except:
                answer = answer_str

        print(f"Computed Answer: {answer}")

        # 4. Submit
        result = submit_answer(submit_url, answer, current_url)
        print(f"Submission Result: {result}")

        # 5. Decide Next Step
        if result.get("correct"):
            next_url = result.get("url")
            if next_url:
                current_url = next_url
            else:
                print("Quiz Completed Successfully!")
                break
        else:
            print("Answer Incorrect. Retrying not implemented (risk of infinite loop).")
            # Optional: Retry logic could go here
            break

# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------
@app.post("/")
async def start_quiz(task: QuizRequest, background_tasks: BackgroundTasks):
    if task.secret != STUDENT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # Start the loop in the background so we don't block the initial request
    # BUT, the requirements say "Your script must... submit the correct answer... within 3 minutes".
    # The initial POST expects a 200 OK immediately? 
    # "Respond with a HTTP 200 JSON response if the secret matches... Visit the url and solve the quiz"
    # So we MUST return 200 first, then solve.
    
    background_tasks.add_task(solve_quiz_loop, task.url)
    
    return {"message": "Quiz processing started", "status": "ok"}

@app.get("/")
def home():
    return {"status": "running", "service": "tds-llm-solver-tp2"}
