# LLM Analysis Quiz Solver

This is a robust, autonomous agent designed to solve data analysis quizzes using LLMs and Python tools.

## Features
- **Recursive Solving**: Automatically follows new URLs until the quiz is complete.
- **Tool Use**: Can download files, read PDFs/CSVs, and execute Python code for calculations.
- **Resilient**: Handles timeouts and errors gracefully.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

2.  **Environment Variables**:
    Ensure your `.env` file has:
    ```
    GEMINI_API_KEY=...
    STUDENT_EMAIL=...
    STUDENT_SECRET=...
    ```

3.  **Run Locally**:
    ```bash
    uvicorn main:app --reload
    ```

## Deployment (Render)
This project is configured for Render using **Docker**.
1.  Push this folder to GitHub.
2.  Create a new Web Service on Render.
3.  Connect your repo.
4.  **Important**: Select **Docker** as the Runtime (or Environment).
5.  Set the Root Directory to `TP2` (if you pushed the whole repo) or just use the `render.yaml` configuration.
6.  Add your Environment Variables in the Render dashboard.

## Testing
Send a POST request to your endpoint:
```json
{
  "email": "your-email",
  "secret": "your-secret",
  "url": "https://tds-llm-analysis.s-anand.net/demo"
}
```
