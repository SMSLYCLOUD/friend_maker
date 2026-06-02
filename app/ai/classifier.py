import json
import logging
import re
from typing import Dict, Any, Optional, List
from app.ai.openrouter_manager import OpenRouterManager

class ProfileClassifier:
    def __init__(self, manager: OpenRouterManager):
        self.manager = manager
        self.logger = logging.getLogger("ProfileClassifier")

    async def classify(self, profile_data: Dict[str, Any], image_base64: Optional[str] = None, bot_instructions: str = "", ref_images: List[str] = None) -> Dict[str, Any]:
        rules = ""
        if bot_instructions:
            rules = f"""
FILTERING RULES (these are MANDATORY — skip profiles that match any of these):
{bot_instructions}

You MUST check these rules and set "should_skip": true and "skip_reason" if the profile violates any rule.
"""
        ref_hint = ""
        if ref_images:
            ref_hint = f"\n(I have attached {len(ref_images)} reference image(s) of the IDEAL target profile type. Compare the target profile against these references. A profile that looks similar to the references should get a higher match_score.)"

        prompt = f"""
Analyze the following social media profile and return a JSON object.
Do NOT include any markdown formatting (like ```json). Just the raw JSON string.

Profile:
Username: {profile_data.get('username')}
Bio: {profile_data.get('bio', 'N/A')}
Followers: {profile_data.get('followers', 0)}
Posts: {profile_data.get('posts', 0)}

{"(I have attached a screenshot of the profile for visual analysis.)" if image_base64 else ""}{ref_hint}

Task:
1. Identify the 'niche' (e.g., Tech, Fitness, Business).
2. Determine 'account_type' (Personal, Business, Bot, Influencer).
3. Calculate 'match_score' (0.0 to 1.0) for a target audience interested in Software Development and AI.
4. Check if the profile should be SKIPPED based on the filtering rules below.{rules}

Return format:
{{
  "niche": "string",
  "account_type": "string",
  "match_score": float,
  "should_skip": bool,
  "skip_reason": "string or null",
  "reasoning": "string"
}}
"""
        response = await self.manager.generate(prompt, image_base64=image_base64, ref_images=ref_images)
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
