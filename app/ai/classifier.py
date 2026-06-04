import json
import logging
import re
from typing import Dict, Any, Optional, List
from app.ai.openrouter_manager import OpenRouterManager

logger = logging.getLogger("ProfileClassifier")

# Common female name indicators
FEMALE_INDICATORS = [
    "she", "her", "hers", "girl", "woman", "female", "queen", "princess",
    "baddie", "softie", "aesthetic", "coquette", "angel", "doll",
    "mrs", "miss", "ms", "lady", "sis", "sister", "queen",
    "feminine", "girly", "pretty", "cute", "beautiful",
]

# Common male name indicators
MALE_INDICATORS = [
    "he", "him", "his", "boy", "man", "male", "king", "bro",
    "dude", "guy", "sir", "mr", "king", "prince", "boss",
    "masculine", "manly", "brother", "brotherhood",
]

# Bot/spam indicators
BOT_INDICATORS = [
    "bot", "automated", "ai ", "chatgpt", "gpt", "openai",
    "follow for follow", "f4f", "like for like", "l4l",
    "dm for promo", "promo", "collab", "spon",
    "link in bio", "click here", "free followers",
    "earn money", "make money", "work from home",
    "crypto", "nft", "forex", "trading",
]


def _parse_follower_count(followers) -> int:
    """Parse follower count from various formats."""
    if isinstance(followers, (int, float)):
        return int(followers)
    if not followers:
        return 0
    s = str(followers).replace(",", "").replace(" ", "").lower()
    if s.endswith("k"):
        try: return int(float(s[:-1]) * 1000)
        except: return 0
    elif s.endswith("m"):
        try: return int(float(s[:-1]) * 1000000)
        except: return 0
    elif s.endswith("b"):
        try: return int(float(s[:-1]) * 1000000000)
        except: return 0
    try:
        return int(s)
    except:
        return 0


def _detect_gender(profile_data: Dict[str, Any]) -> str:
    """Detect gender from profile data. Returns 'male', 'female', or 'unknown'."""
    text = " ".join([
        profile_data.get("username", ""),
        profile_data.get("display_name", ""),
        profile_data.get("bio", ""),
    ]).lower()

    female_score = sum(1 for w in FEMALE_INDICATORS if w in text)
    male_score = sum(1 for w in MALE_INDICATORS if w in text)

    if female_score > male_score and female_score >= 1:
        return "female"
    elif male_score > female_score and male_score >= 1:
        return "male"
    return "unknown"


def _is_bot(profile_data: Dict[str, Any]) -> bool:
    """Detect bot/spam accounts."""
    text = " ".join([
        profile_data.get("username", ""),
        profile_data.get("display_name", ""),
        profile_data.get("bio", ""),
    ]).lower()

    for indicator in BOT_INDICATORS:
        if indicator in text:
            return True
    return False


class ProfileClassifier:
    def __init__(self, manager: OpenRouterManager):
        self.manager = manager

    def _extract_filter_criteria(self, instructions: str) -> str:
        """Extract only filtering criteria from complex instructions."""
        if not instructions:
            return ""
        filter_lines = []
        for line in instructions.split("\n"):
            lower = line.strip().lower()
            if any(kw in lower for kw in [
                "skip", "filter", "only process", "only engage", "only message",
                "do not", "don't", "no ", "exclude", "avoid", "male only",
                "female", "gender", "bot", "spam", "fake", "private",
                "verified", "followers", "no bio", "no profile",
                "no filtering", "only filter",
            ]):
                filter_lines.append(line.strip())
        return "\n".join(filter_lines) if filter_lines else ""

    def _check_filters(self, profile_data: Dict[str, Any], instructions: str) -> Optional[str]:
        """Programmatic filter checks based on instructions. Returns skip_reason or None."""
        instructions_lower = instructions.lower()

        # Gender filter — only if instructions mention it
        if any(kw in instructions_lower for kw in ["male only", "only male", "only process male", "skip female", "gender"]):
            gender = _detect_gender(profile_data)
            if gender == "female":
                return "female_account"
            # If unknown and instructions say male only, skip to be safe
            if gender == "unknown" and "male only" in instructions_lower:
                return "unknown_gender"

        # Bot/spam filter
        if any(kw in instructions_lower for kw in ["bot", "spam", "fake", "automated"]):
            if _is_bot(profile_data):
                return "bot_or_spam"

        # Follower count filters
        followers = _parse_follower_count(profile_data.get("follower_count") or profile_data.get("followers"))

        # Check for minimum followers
        m = re.search(r'(?:skip|min|minimum|less than|under|below)\s+(\d+)\s*(?:k)?\s*(?:followers?)?', instructions_lower)
        if m:
            min_f = int(m.group(1))
            if "k" in m.group(0): min_f *= 1000
            if 0 < followers < min_f:
                return f"followers_below_{min_f}"

        # Check for maximum followers
        m = re.search(r'(?:skip|max|maximum|more than|over|above|greater than)\s+(\d+)\s*(?:k)?\s*(?:followers?)?', instructions_lower)
        if m:
            max_f = int(m.group(1))
            if "k" in m.group(0): max_f *= 1000
            if followers > max_f:
                return f"followers_above_{max_f}"

        # Private account check
        if any(kw in instructions_lower for kw in ["skip private", "private accounts", "no private"]):
            if profile_data.get("is_private"):
                return "private_account"

        return None

    async def classify(self, profile_data: Dict[str, Any], image_base64: Optional[str] = None,
                       bot_instructions: str = "", ref_images: List[str] = None,
                       campaign_instructions: str = "") -> Dict[str, Any]:
        # Merge instructions
        combined = ""
        if bot_instructions:
            combined = bot_instructions
        if campaign_instructions:
            combined = combined + "\n" + campaign_instructions if combined else campaign_instructions

        # Run programmatic filters FIRST — these are reliable
        filter_result = self._check_filters(profile_data, combined)
        if filter_result:
            logger.info(f"Filter skip: {filter_result} for @{profile_data.get('username')}")
            return {
                "should_skip": True,
                "skip_reason": filter_result,
                "match_score": 0.0,
                "niche": "",
                "account_type": "",
                "reasoning": f"Filtered: {filter_result}"
            }

        # Only use LLM for niche/account_type detection — NOT for filtering
        prompt = f"""Analyze this social media profile. Return JSON only, no markdown.

Profile:
Username: {profile_data.get('username')}
Bio: {profile_data.get('bio', 'N/A')}
Display Name: {profile_data.get('display_name', 'N/A')}
Follower Count: {profile_data.get('follower_count', profile_data.get('followers', 'N/A'))}

Return:
{{"niche": "string", "account_type": "string", "match_score": 0.5, "reasoning": "brief"}}"""

        try:
            response = await self.manager.generate(prompt, image_base64=image_base64, ref_images=ref_images)
            result = self._parse_json(response)
            result.setdefault("niche", "")
            result.setdefault("account_type", "")
            result.setdefault("match_score", 0.5)
            result.setdefault("reasoning", "")
            # NEVER let LLM override our programmatic filters
            result["should_skip"] = False
            result["skip_reason"] = None
            return result
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return {
                "should_skip": False,
                "skip_reason": None,
                "match_score": 0.5,
                "niche": "",
                "account_type": "",
                "reasoning": f"LLM error: {e}"
            }

    def _parse_json(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```', '', text)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            return {}
