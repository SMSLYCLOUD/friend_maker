import json
import logging
import re
import base64
from typing import Dict, Any, Optional, List
from app.ai.openrouter_manager import OpenRouterManager

logger = logging.getLogger("ProfileClassifier")


def _parse_follower_count(followers) -> int:
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
    try:
        return int(s)
    except:
        return 0


def _detect_gender_text(profile_data: Dict[str, Any]) -> str:
    """Text-based gender detection from username, display name, bio."""
    text = " ".join([
        profile_data.get("username", ""),
        profile_data.get("display_name", ""),
        profile_data.get("bio", ""),
    ]).lower()

    female_kw = ["she", "her", "girl", "woman", "female", "queen", "princess",
                  "baddie", "aesthetic", "coquette", "angel", "doll", "mrs", "miss",
                  "lady", "sis", "sister", "feminine", "girly"]
    male_kw = ["he", "him", "boy", "man", "male", "king", "bro", "dude", "guy",
               "sir", "mr", "prince", "boss", "masculine", "brother"]

    f_score = sum(1 for w in female_kw if w in text)
    m_score = sum(1 for w in male_kw if w in text)

    if f_score > m_score and f_score >= 1:
        return "female"
    elif m_score > f_score and m_score >= 1:
        return "male"
    return "unknown"


def _is_bot_text(profile_data: Dict[str, Any]) -> bool:
    text = " ".join([
        profile_data.get("username", ""),
        profile_data.get("display_name", ""),
        profile_data.get("bio", ""),
    ]).lower()
    bot_kw = ["bot", "automated", "ai ", "chatgpt", "gpt",
              "follow for follow", "f4f", "like for like", "l4l",
              "dm for promo", "promo", "collab", "link in bio",
              "click here", "free followers", "earn money", "crypto", "nft"]
    return any(w in text for w in bot_kw)


class ProfileClassifier:
    def __init__(self, manager: OpenRouterManager):
        self.manager = manager

    def _extract_filter_criteria(self, instructions: str) -> str:
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

    def _check_text_filters(self, profile_data: Dict[str, Any], instructions: str) -> Optional[str]:
        """Programmatic text-based filter checks. Returns skip_reason or None."""
        instructions_lower = instructions.lower()

        # Gender filter
        has_gender_filter = any(kw in instructions_lower for kw in [
            "male only", "only male", "only process male", "skip female",
            "gender filter", "gender", "only male"
        ])
        if has_gender_filter:
            gender = _detect_gender_text(profile_data)
            if gender == "female":
                return "female_account"

        # Bot/spam filter
        if any(kw in instructions_lower for kw in ["bot", "spam", "fake", "automated"]):
            if _is_bot_text(profile_data):
                return "bot_or_spam"

        # Follower count filters
        followers = _parse_follower_count(profile_data.get("follower_count") or profile_data.get("followers"))

        m = re.search(r'(?:skip|min|minimum|less than|under|below)\s+(\d+)\s*(?:k)?\s*(?:followers?)?', instructions_lower)
        if m:
            min_f = int(m.group(1))
            if "k" in m.group(0): min_f *= 1000
            if 0 < followers < min_f:
                return f"followers_below_{min_f}"

        m = re.search(r'(?:skip|max|maximum|more than|over|above|greater than)\s+(\d+)\s*(?:k)?\s*(?:followers?)?', instructions_lower)
        if m:
            max_f = int(m.group(1))
            if "k" in m.group(0): max_f *= 1000
            if followers > max_f:
                return f"followers_above_{max_f}"

        # Private account
        if any(kw in instructions_lower for kw in ["skip private", "private accounts", "no private"]):
            if profile_data.get("is_private"):
                return "private_account"

        return None

    async def classify(self, profile_data: Dict[str, Any], screenshot_b64: Optional[str] = None,
                       bot_instructions: str = "", ref_images: List[str] = None,
                       campaign_instructions: str = "") -> Dict[str, Any]:
        # Merge instructions
        combined = ""
        if bot_instructions:
            combined = bot_instructions
        if campaign_instructions:
            combined = combined + "\n" + campaign_instructions if combined else campaign_instructions

        # Step 1: Fast text-based filters
        text_filter = self._check_text_filters(profile_data, combined)
        if text_filter:
            logger.info(f"Text filter skip: {text_filter} for @{profile_data.get('username')}")
            return {
                "should_skip": True,
                "skip_reason": text_filter,
                "match_score": 0.0,
                "niche": "",
                "account_type": "",
                "reasoning": f"Text filter: {text_filter}"
            }

        # Step 2: LLM verification with screenshot (if available)
        filter_criteria = self._extract_filter_criteria(combined)

        prompt = f"""You are a social media profile classifier. Analyze this profile and decide if it should be SKIPPED.

Profile Data:
Username: {profile_data.get('username')}
Bio: {profile_data.get('bio', 'N/A')}
Display Name: {profile_data.get('display_name', 'N/A')}
Follower Count: {profile_data.get('follower_count', profile_data.get('followers', 'N/A'))}
Is Private: {profile_data.get('is_private', False)}

{"FILTERING RULES — you MUST enforce these:" if filter_criteria else ""}
{filter_criteria}

{"A screenshot of the profile is attached. Use it to determine:" if screenshot_b64 else ""}
{"- Gender (from profile picture and display name)" if screenshot_b64 else ""}
{"- Whether this looks like a real person or a bot/spam account" if screenshot_b64 else ""}

DECISION RULES:
- If rules say "male only" and you can clearly see this is a female profile → skip
- If profile looks like a bot/spam → skip
- If you CANNOT determine gender from the screenshot → DO NOT skip (proceed)
- If no screenshot available and gender is unclear → DO NOT skip

Return JSON only (no markdown):
{{"should_skip": false, "skip_reason": null, "match_score": 0.5, "niche": "", "account_type": "", "gender_guess": "unknown", "reasoning": "brief explanation"}}"""

        try:
            response = await self.manager.generate(prompt, image_base64=screenshot_b64, ref_images=ref_images)
            result = self._parse_json(response)

            # LLM can only SET skip, never override text filters
            if result.get("should_skip") and not result.get("skip_reason"):
                result["should_skip"] = False
                result["skip_reason"] = None

            result.setdefault("should_skip", False)
            result.setdefault("skip_reason", None)
            result.setdefault("match_score", 0.5)
            result.setdefault("niche", "")
            result.setdefault("account_type", "")
            result.setdefault("reasoning", "")
            return result
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return {
                "should_skip": False, "skip_reason": None, "match_score": 0.5,
                "niche": "", "account_type": "", "reasoning": f"LLM error: {e}"
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
