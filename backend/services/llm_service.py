import os

from dotenv import load_dotenv
from google import genai

load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set in the .env file."
    )


client = genai.Client(api_key=GEMINI_API_KEY)


# Gemini model used for answering questions
GEMINI_MODEL = "gemini-2.5-flash"


def generate_answer(system_instruction, prompt):
    """
    Send a prompt to Gemini and return the generated answer.
    """

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "system_instruction": system_instruction,
            "temperature": 0.1,
        },
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text.strip()