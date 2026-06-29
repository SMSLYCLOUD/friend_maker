import logging
import re
from typing import Optional

logger = logging.getLogger("MessageValidator")

# Patterns that indicate AI refusal or leaked content
# These are intentionally strict to avoid false-positives on normal conversation.
REFUSAL_PATTERNS = [
    # Self-identification as AI
    r"i(?:'m| am) (?:an |a )?ai",
    r"as an ai",
    r"as a (?:language model|AI assistant|virtual assistant)",
    # Refusing to comply
    r"i (?:must|have to) (?:decline|refuse|refrain)",
    r"sorry,? (?:but |however )?i (?:can(?:not|'?t)|won't|am unable)",
    r"i (?:apologize|apologise) (?:but |, )?(?:i |i'm )?(?:can(?:not|'?t)|won't)",
    r"i (?:don'?t|do not) (?:make|send|generate) (?:unsolicited|automated)",
    # Mentioning internal policies
    r"(?:ethical|safety) (?:guidelines|rules|constraints)",
    r"terms of (?:service|use)",
    r"community (?:guidelines|standards)",
    # Talking about limitations
    r"my (?:capabilities|abilities|programming) (?:are|do not|don't|limit)",
    r"i (?:can(?:not|'?t)|won't|will not|am not able to|unable to) (?:help|assist|do that|complete|fulfill)",
    # Explicit refusal phrasing
    r"i (?:would|could) (?:suggest|recommend|advise) (?:reaching|speaking|contacting|talking)",
    r"(?:inappropriate|harmful|offensive|explicit) (?:content|material|messages)",
]

# Patterns that indicate leaked internal reasoning
LEAKED_THOUGHT_PATTERNS = [
    # System prompt leakage
    r"(?:system|internal|hidden) (?:prompt|instruction|message)",
    r"(?:here(?:'s| is) what (?:i|we) (?:should|will|need to))",
    r"(?:the (?:user|human) (?:wants|needs|is trying))",
    r"(?:let(?:'s| us) (?:think|analyze|consider|break))",
    r"(?:chain of thought|reasoning|analysis):",
    # Internal instruction headers
    r"(?:task|goal|objective):",
    r"(?:instruction|rule|guideline):",
    r"(?:step \d|step\s+\d)",
    # JSON/code block dump (not simple template vars)
    r"(?:\{[\"'](?:[\w_]+)[\"']:[\s\"'])",
    r"(?:```|~~~)",
    r"(?:<\|.*?\|>)",
    r"(?:\[(?:INST|SYS|USER|ASSISTANT)\])",
    # Full markdown formatting (bold/italic, not single # hashtag)
    r"(?:\*{2}|_{2})",
    # Explicit format leakage
    r"\b(?:json|markdown)(?:\s+(?:object|block|format|response))?(?:s)?\s*(?:\n|$)",
]

# Message quality checks
MIN_MESSAGE_LENGTH = 5
MAX_MESSAGE_LENGTH = 500


def validate_message(message: str, context: str = "") -> tuple[bool, Optional[str]]:
    """
    Validate a generated message. Returns (is_valid, reason).
    If is_valid is False, reason explains why and the message should be retried.
    """
    if not message or not message.strip():
        return False, "Empty message"

    msg = message.strip()

    # Length check
    if len(msg) < MIN_MESSAGE_LENGTH:
        return False, f"Message too short ({len(msg)} chars)"

    if len(msg) > MAX_MESSAGE_LENGTH:
        return False, f"Message too long ({len(msg)} chars, max {MAX_MESSAGE_LENGTH})"

    # Check for refusal patterns
    msg_lower = msg.lower()
    for pattern in REFUSAL_PATTERNS:
        if re.search(pattern, msg_lower):
            return False, f"AI refusal detected: {pattern}"

    # Check for leaked internal thoughts
    for pattern in LEAKED_THOUGHT_PATTERNS:
        if re.search(pattern, msg_lower):
            return False, f"Leaked content detected: {pattern}"

    # Check if message looks like a system/prompt dump (contains multiple newlines with structured content)
    lines = msg.split("\n")
    structured_lines = sum(1 for l in lines if re.match(r'^\s*[-*]\s|^\s*\d+\.\s|^\s*#{1,3}\s', l))
    if structured_lines > len(lines) * 0.5 and len(lines) > 3:
        return False, "Message contains structured/prompt-like content"

    # Check if message is just punctuation or special characters
    alpha_chars = sum(1 for c in msg if c.isalpha())
    if alpha_chars < len(msg) * 0.3:
        return False, "Message has too few alphabetic characters"

    # Check for multiple languages mixed (often a sign of prompt leakage)
    if re.search(r'[\u4e00-\u9fff]', msg) and re.search(r'[a-zA-Z]', msg):
        # Only flag if there's substantial Chinese content
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', msg))
        if chinese_chars > 10:
            return False, "Message contains mixed languages (possible prompt leakage)"

    return True, None
