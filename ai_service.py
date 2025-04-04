import openai
import os
from dotenv import load_dotenv
from typing import List, Optional
import logging

load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sanitize_review_text(text: str) -> str:
    """Sanitize review text to ensure it's suitable for the API."""
    # Remove any non-printable characters
    text = ''.join(char for char in text if char.isprintable())
    # Limit length to avoid token limits
    return text[:1000]  # Adjust this limit based on your needs

def generate_summary(reviews: List) -> str:
    """Generates an AI-powered summary for recruiter reviews."""
    if not reviews:
        return "No reviews available for this recruiter yet."

    try:
        # Prepare and sanitize the prompt
        prompt = "Summarize the following recruiter reviews in a professional and concise manner, focusing on key patterns and overall sentiment:\n\n"
        for review in reviews:
            sanitized_text = sanitize_review_text(review.text)
            if sanitized_text.strip():  # Only add non-empty reviews
                prompt += f"- {sanitized_text}\n"

        if not prompt.strip():
            return "No reviews available for this recruiter yet."

        # Make the API call with error handling
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional recruiter review analyst. Provide concise, objective summaries focusing on patterns and key points."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )

        summary = response.choices[0].message.content.strip()
        
        # Validate the summary
        if not summary or len(summary) < 10:  # Basic validation
            return "Based on the available reviews, this recruiter has received feedback from candidates."
            
        return summary

    except openai.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return "Based on the available reviews, this recruiter has received ambivalent feedback from candidates."
    except Exception as e:
        logger.error(f"Unexpected error in summary generation: {str(e)}")
        return "Based on the available reviews, this recruiter has received ambivalent feedback from candidates." 


