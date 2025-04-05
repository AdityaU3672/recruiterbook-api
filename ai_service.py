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
        # Count total words across all reviews to detect limited information
        total_words = sum(len(review.text.split()) for review in reviews)
        
        # Prepare and sanitize the prompt
        prompt = "Based on the following candidate feedback, create a professional description of this recruiter. Focus on their style, approach, and qualities:\n\n"
        for review in reviews:
            sanitized_text = sanitize_review_text(review.text)
            if sanitized_text.strip():  # Only add non-empty reviews
                prompt += f"- {sanitized_text}\n"

        if not prompt.strip():
            return "No reviews available for this recruiter yet."
            
        # Adjust prompt based on review volume
        if total_words < 20:  # Limited information
            prompt += "\nNote: There is limited information available. Be very brief, factual, and avoid making inferences beyond what is directly stated."
            temperature = 0.3  # Lower temperature for more conservative outputs
        else:
            temperature = 0.7
            
        # Make the API call with error handling
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are creating professional profile descriptions for recruiters based on candidate reviews. Write in third person about the recruiter, not about the reviews themselves. Focus only on what can be directly inferred from the reviews. Be conservative with limited information - if there's not much to say, keep it very brief and factual. Never embellish or make up qualities not evidenced in the reviews."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=temperature
        )

        summary = response.choices[0].message.content.strip()
        
        # Validate the summary
        if not summary or len(summary) < 10:  # Basic validation
            return "Based on the available reviews, this recruiter has received feedback from candidates."
        
        # For reviews with limited information, enforce brevity
        if total_words < 20 and len(summary) > 100:
            return "This recruiter has limited feedback from candidates. More reviews are needed for a comprehensive profile."
            
        return summary

    except openai.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return "Based on the available reviews, this recruiter has received feedback from candidates."
    except Exception as e:
        logger.error(f"Unexpected error in summary generation: {str(e)}")
        return "Based on the available reviews, this recruiter has received feedback from candidates." 


