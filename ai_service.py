import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_summary(reviews):
    """Generates an AI-powered summary for recruiter reviews."""
    if not reviews:
        return "No reviews available."

    prompt = "Summarize the following recruiter reviews in a few sentences:\n\n"
    for review in reviews:
        prompt += f"- {review.text}\n"

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are an AI that summarizes recruiter reviews."},
                  {"role": "user", "content": prompt}],
        max_tokens=150
    )

    return response["choices"][0]["message"]["content"].strip()
