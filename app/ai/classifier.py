import json
import logging
import re
from typing import Dict, Any, Optional, List
from app.ai.openrouter_manager import OpenRouterManager

class ProfileClassifier:
    def __init__(self, manager: OpenRouterManager):
        self.manager = manager
        self.logger = logging.getLogger("ProfileClassifier")

    def _extract_filter_criteria(self, instructions: str) -> str:
        """Extract only filtering criteria from complex instructions."""
        if not instructions:
            return ""

        filter_lines = []
        lines = instructions.split("\n")
        for line in lines:
            lower = line.strip().lower()
            # Lines that describe what to skip/filter
            if any(kw in lower for kw in [
                "skip", "filter", "only process", "only engage", "only message",
                "do not", "don't", "no ", "exclude", "avoid", "male only",
                "female", "gender", "bot", "spam", "fake", "private",
                "verified", "followers", "no bio", "no profile",
                "no filtering", "only filter",
            ]):
                filter_lines.append(line.strip())

        return "\n".join(filter_lines) if filter_lines else ""

    def pre_filter(self, profile_data: Dict[str, Any], bot_instructions: str = "") -> Optional[str]:
        """Fast programmatic checks before LLM call. Returns skip_reason or None."""
        username = (profile_data.get("username") or "").lower()
        bio = (profile_data.get("bio") or "").lower()
        followers = profile_data.get("followers") or 0

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

        lines = bot_instructions.split("\n") if bot_instructions else []
        for line in lines:
            line = line.strip().lstrip("- ").lower()

            m = re.search(r'(?:skip|min|minimum|less than|under|below)\s+(\d+)\s*(?:k)?\s*(?:followers?)?', line)
            if m:
                min_f = int(m.group(1))
                if line.endswith("k"): min_f *= 1000
                if 0 < followers < min_f:
                    return f"followers_below_{min_f}"

            m = re.search(r'(?:skip|max|maximum|more than|over|above|greater than)\s+(\d+)\s*(?:k)?\s*(?:followers?)?', line)
            if m:
                max_f = int(m.group(1))
                if "k" in line.split(str(max_f))[1][:3]: max_f *= 1000
                if followers > max_f:
                    return f"followers_above_{max_f}"

            if "no profile pic" in line or "without profile pic" in line or "no profile photo" in line or "without profile photo" in line:
                if profile_data.get("has_profile_pic") is False:
                    return "no_profile_pic"

            if ("no bio" in line or "empty bio" in line or "without bio" in line) and not bio:
                return "empty_bio"

            if "skip bot" in line or "no bots" in line or "skip automated" in line:
                if profile_data.get("account_type", "").lower() in ("bot", "automated"):
                    return "bot_account"

            if ("skip verified" in line or "no verified" in line or "skip blue check" in line):
                if profile_data.get("is_verified"):
                    return "verified_account"

            if ("skip private" in line or "private accounts" in line or "no private" in line):
                if profile_data.get("is_private"):
                    return "private_account"

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
        # Merge bot_instructions with campaign_instructions for filtering rules
        combined_instructions = ""
        if bot_instructions:
            combined_instructions = bot_instructions
        if campaign_instructions:
            if combined_instructions:
                combined_instructions = combined_instructions + "\n" + campaign_instructions
            else:
                combined_instructions = campaign_instructions

        self.logger.info(f"classify: bot_instructions={len(bot_instructions)} chars, campaign_instructions={len(campaign_instructions)} chars, combined={len(combined_instructions)} chars")

        # Run fast pre-filters first
        pre_skip = self.pre_filter(profile_data, combined_instructions)
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

        # Extract only filtering criteria from the instructions
        filter_criteria = self._extract_filter_criteria(combined_instructions)

        ref_hint = ""
        if ref_images:
            ref_hint = f"\n(I have attached {len(ref_images)} reference image(s) of the IDEAL target profile type. Compare the target profile against these references.)"

        # Build focused filtering prompt
        filtering_section = ""
        if filter_criteria:
            filtering_section = f"""
FILTERING RULES (apply these to decide should_skip):
{filter_criteria}

Based on the profile data above, determine if this profile should be SKIPPED based on the rules.
- Set "should_skip" to true if the profile clearly violates ANY rule
- Set "skip_reason" to which rule was violated
- If you CANNOT determine whether a rule applies (e.g., can't determine gender), set should_skip to false
- DO NOT skip just because data is missing — only skip for clear violations
"""

        prompt = f"""Analyze this social media profile and return a JSON object.
Do NOT include any markdown formatting. Just the raw JSON string.

Profile:
Username: {profile_data.get('username')}
Bio: {profile_data.get('bio', 'N/A')}
Display Name: {profile_data.get('display_name', 'N/A')}
Follower Count: {profile_data.get('follower_count', profile_data.get('followers', 'N/A'))}
Recent Posts: {', '.join(profile_data.get('recent_posts', [])[:3]) if profile_data.get('recent_posts') else 'N/A'}
Is Private: {profile_data.get('is_private', False)}
{"(Screenshot attached)" if image_base64 else ""}{ref_hint}

{filtering_section}
OTHER TASKS:
1. "niche" — the profile's category (e.g., Tech, Music, Fitness)
2. "account_type" — Personal, Business, Bot, Influencer, or Media
3. "match_score" — 0.0 to 1.0, how well this profile matches the target audience
   - 0.5 if you can't determine relevance from available data
   - Never give 0.0 for missing data

Return format:
{{
  "niche": "string",
  "account_type": "string",
  "match_score": 0.5,
  "should_skip": false,
  "skip_reason": null,
  "reasoning": "brief explanation"
}}
"""
        response = await self.manager.generate(prompt, image_base64=image_base64, ref_images=ref_images)
        result = self._parse_json(response)

        # Override: ignore should_skip from LLM if no rules exist
        if not filter_criteria and result.get("should_skip"):
            self.logger.info(f"Ignoring LLM skip (no filter criteria found) — using score only")
            result["should_skip"] = False
            result["skip_reason"] = None

        return result

    def _parse_json(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}

        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```', '', text)
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from AI response: {text}")
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            return {}
