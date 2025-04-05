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
        # Count total words and analyze review content
        total_words = sum(len(review.text.split()) for review in reviews)
        extremely_limited = total_words <= 2  # Extremely limited info (e.g., "Good" or single-word responses)
        limited_info = total_words < 20 and not extremely_limited  # Limited but usable info
        
        # Prepare and sanitize the prompt
        prompt = "Based on the following candidate feedback, create a professional description of this recruiter. Focus on their style, approach, and qualities:\n\n"
        for review in reviews:
            sanitized_text = sanitize_review_text(review.text)
            if sanitized_text.strip():  # Only add non-empty reviews
                prompt += f"- {sanitized_text}\n"

        if not prompt.strip():
            return "No reviews available for this recruiter yet."
            
        # Adjust prompt based on review volume
        if extremely_limited:
            # For extremely limited info, use default message
            return "This recruiter has limited feedback from candidates. More reviews are needed for a comprehensive profile."
        elif limited_info:
            prompt += "\nNote: There is limited information available. Create a very brief, factual summary that directly incorporates the specific feedback provided. Do not add any details beyond what is explicitly mentioned."
            temperature = 0.2  # Very low temperature for almost deterministic outputs
        else:
            prompt += "\nCreate a concise profile that balances being informative with staying true to the feedback provided."
            temperature = 0.7
            
        # Make the API call with error handling
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are creating professional profile descriptions for recruiters based on candidate reviews. Write in third person about the recruiter, not about the reviews themselves. Always incorporate specific details from the reviews. Never embellish or make up qualities not evidenced in the reviews. When information is limited, create a brief 1-2 sentence summary focusing on the specific feedback provided."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=temperature
        )

        summary = response.choices[0].message.content.strip()
        
        # Basic validation
        if not summary or len(summary) < 10:
            return "Based on the available reviews, this recruiter has received feedback from candidates."
        
        # For limited information, enforce reasonable brevity but don't default to generic message
        if limited_info and len(summary) > 120:
            # Try to extract the first sentence if it's reasonably concise
            first_sentence = summary.split('.')[0]
            if len(first_sentence) > 30:  # First sentence is substantial enough
                return first_sentence + "."
            else:
                # Use first two sentences if first is too brief
                sentences = summary.split('.')
                if len(sentences) > 1 and len(sentences[0] + sentences[1]) < 120:
                    return sentences[0] + "." + sentences[1] + "."
                else:
                    return "This recruiter's feedback mentions " + summary.split()[0].lower() + " " + summary.split()[1].lower() + " " + summary.split()[2].lower() + "..."
            
        return summary

    except openai.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return "Based on the available reviews, this recruiter has received feedback from candidates."
    except Exception as e:
        logger.error(f"Unexpected error in summary generation: {str(e)}")
        return "Based on the available reviews, this recruiter has received feedback from candidates." 


