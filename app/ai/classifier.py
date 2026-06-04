import json
import logging
import re
from typing import Dict, Any, Optional, List
from app.ai.openrouter_manager import OpenRouterManager

class ProfileClassifier:
    def __init__(self, manager: OpenRouterManager):
        self.manager = manager
        self.logger = logging.getLogger("ProfileClassifier")

    def pre_filter(self, profile_data: Dict[str, Any], bot_instructions: str = "") -> Optional[str]:
        """Fast programmatic checks before LLM call. Returns skip_reason or None."""
        username = (profile_data.get("username") or "").lower()
        bio = (profile_data.get("bio") or "").lower()
        followers = profile_data.get("followers") or 0

        # Parse follower count from string like "1.2K" or "12,345"
        if isinstance(followers, str):
            followers = followers.replace(",", "").replace(" ", "")
            if followers.endswith("k"):
                try: followers = int(float(followers[:-1]) * 1000)
                except: followers = 0
            elif followers.endswith("m"):
                try: followers = int(float(followers[:-1]) * 1000000)
                except: followers = 0
            else:
                try: followers = int(followers)
                except: followers = 0

        # Check bot_instructions for structured rules
        lines = bot_instructions.split("\n") if bot_instructions else []
        for line in lines:
            line = line.strip().lstrip("- ").lower()

            # "skip followers less than X"
            m = re.search(r'(?:skip|min|minimum|less than|under|below)\s+(\d+)\s*(?:k)?\s*(?:followers?)?', line)
            if m:
                min_f = int(m.group(1))
                if line.endswith("k"): min_f *= 1000
                if 0 < followers < min_f:
                    return f"followers_below_{min_f}"

            # "skip followers more than X" or "skip accounts with more than X followers"
            m = re.search(r'(?:skip|max|maximum|more than|over|above|greater than)\s+(\d+)\s*(?:k)?\s*(?:followers?)?', line)
            if m:
                max_f = int(m.group(1))
                if "k" in line.split(str(max_f))[1][:3]: max_f *= 1000
                if followers > max_f:
                    return f"followers_above_{max_f}"

            # "skip accounts with no profile pic" / "skip accounts without profile photo"
            if "no profile pic" in line or "without profile pic" in line or "no profile photo" in line or "without profile photo" in line:
                if profile_data.get("has_profile_pic") is False:
                    return "no_profile_pic"

            # "skip accounts with no bio" / "skip empty bio"
            if ("no bio" in line or "empty bio" in line or "without bio" in line) and not bio:
                return "empty_bio"

            # "skip bots" / "skip bot accounts"
            if "skip bot" in line or "no bots" in line or "skip automated" in line:
                if profile_data.get("account_type", "").lower() in ("bot", "automated"):
                    return "bot_account"

            # "skip verified" / "no verified accounts"
            if ("skip verified" in line or "no verified" in line or "skip blue check" in line):
                if profile_data.get("is_verified"):
                    return "verified_account"

            # "skip private" / "private accounts"
            if ("skip private" in line or "private accounts" in line or "no private" in line):
                if profile_data.get("is_private"):
                    return "private_account"

            # Bio keyword filters: "skip if bio contains X" / "avoid X in bio"
            m = re.search(r'(?:skip|avoid|no|ban)\s+.*?(?:bio|name).*?(?:contains?|has|includes?)\s+[\"\']*(.+?)[\"\']*(?:\s+or\s+[\"\']*(.+?)[\"\']*)?\s*$', line)
            if m:
                keywords = [m.group(1).strip()]
                if m.group(2): keywords.append(m.group(2).strip())
                for kw in keywords:
                    if kw.lower() in bio or kw.lower() in username:
                        return f"bio_contains_{kw}"

        return None

    async def classify(self, profile_data: Dict[str, Any], image_base64: Optional[str] = None,
                       bot_instructions: str = "", ref_images: List[str] = None,
                       campaign_instructions: str = "") -> Dict[str, Any]:
        # Run fast pre-filters first
        pre_skip = self.pre_filter(profile_data, bot_instructions)
        if pre_skip:
            self.logger.info(f"Pre-filter skip: {pre_skip} for @{profile_data.get('username')}")
            return {
                "should_skip": True,
                "skip_reason": pre_skip,
                "match_score": 0.0,
                "niche": "",
                "account_type": "",
                "reasoning": f"Pre-filtered: {pre_skip}"
            }

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

        audience = campaign_instructions if campaign_instructions else "the target audience described in the campaign instructions"

        prompt = f"""
Analyze the following social media profile and return a JSON object.
Do NOT include any markdown formatting (like ```json). Just the raw JSON string.

Profile:
Username: {profile_data.get('username')}
Bio: {profile_data.get('bio', 'N/A')}
Display Name: {profile_data.get('display_name', 'N/A')}
Follower Count: {profile_data.get('follower_count', profile_data.get('followers', 'N/A'))}
Recent Posts: {', '.join(profile_data.get('recent_posts', [])[:3]) if profile_data.get('recent_posts') else 'N/A'}

{"(I have attached a screenshot of the profile for visual analysis.)" if image_base64 else ""}{ref_hint}

Task:
1. Identify the 'niche' (e.g., Tech, Fitness, Business, Politics, Entertainment).
2. Determine 'account_type' (Personal, Business, Bot, Influencer, Media).
3. Calculate 'match_score' (0.0 to 1.0) — how well does this profile match the target audience: {audience}?
   - A score of 1.0 means perfect match
   - A score of 0.5 means neutral/uncertain
   - A score of 0.0 means clearly not a match
   - DO NOT give a 0.0 score just because data is missing. If you can't determine relevance, give 0.5.
4. If there are filtering rules below, check if the profile violates any. Set "should_skip" only for rules that EXPLICITLY match.{rules}

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
        result = self._parse_json(response)

        # Override: ignore should_skip from LLM if no rules exist — only pre_filter decides skipping
        if not bot_instructions and result.get("should_skip"):
            self.logger.info(f"Ignoring LLM skip (no rules set) — using score only")
            result["should_skip"] = False
            result["skip_reason"] = None

        return result

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
