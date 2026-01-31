import json
import logging
import re
from typing import Dict, Any
from app.ai.ollama_manager import OllamaManager

class ProfileClassifier:
    def __init__(self, manager: OllamaManager):
        self.manager = manager
        self.logger = logging.getLogger("ProfileClassifier")

    async def classify(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
Analyze the following social media profile and return a JSON object.
Do NOT include any markdown formatting (like ```json). Just the raw JSON string.

Profile:
Username: {profile_data.get('username')}
Bio: {profile_data.get('bio', 'N/A')}
Followers: {profile_data.get('followers', 0)}
Posts: {profile_data.get('posts', 0)}

Task:
1. Identify the 'niche' (e.g., Tech, Fitness, Business).
2. Determine 'account_type' (Personal, Business, Bot, Influencer).
3. Calculate 'match_score' (0.0 to 1.0) for a target audience interested in Software Development and AI.

Return format:
{{
  "niche": "string",
  "account_type": "string",
  "match_score": float,
  "reasoning": "string"
}}
"""
        response = await self.manager.generate(prompt)
        return self._parse_json(response)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}

        # Strip markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```', '', text)
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from AI response: {text}")
            # Try to find { ... }
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            return {}
