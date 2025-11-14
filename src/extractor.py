import openai
import json
import time
from typing import Dict


class ControversyAnalyzer:
    def __init__(self, api_key, model="gpt-4o-mini"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def analyze_controversy(self, tweet_text: str) -> Dict:
        """
        Analyze if a tweet is controversial using OpenAI.
        
        Args:
            tweet_text: The text content of the tweet
            
        Returns:
            Dictionary with analysis results including:
            - is_controversial: bool
            - controversy_score: int (0-10)
            - reasons: list of strings
            - topics: list of strings
        """
        prompt = f"""Analyze if this tweet is controversial. Consider:
- Polarizing political statements
- Offensive language
- Misinformation claims
- Inflammatory rhetoric
- Hot-button topics

Tweet: {tweet_text}

Respond with valid JSON only (no markdown, no code blocks):
{{
    "is_controversial": true/false,
    "controversy_score": 0-10,
    "reasons": ["reason1", "reason2"],
    "topics": ["politics", "religion", etc]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            result = json.loads(content)
            
            # Ensure all required fields exist
            return {
                "is_controversial": result.get("is_controversial", False),
                "controversy_score": result.get("controversy_score", 0),
                "reasons": result.get("reasons", []),
                "topics": result.get("topics", [])
            }
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Response content: {content[:200]}")
            # Return default structure on parse error
            return {
                "is_controversial": False,
                "controversy_score": 0,
                "reasons": ["Failed to parse AI response"],
                "topics": []
            }
        except openai.RateLimitError:
            print("OpenAI rate limit exceeded. Waiting 60 seconds...")
            time.sleep(60)
            # Retry once
            return self.analyze_controversy(tweet_text)
        except Exception as e:
            print(f"Error analyzing tweet: {e}")
            return {
                "is_controversial": False,
                "controversy_score": 0,
                "reasons": [f"Analysis error: {str(e)}"],
                "topics": []
            }