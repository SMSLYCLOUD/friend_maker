"""Custom exceptions for the SocialGrowthAI platform."""


class BlockerDetected(Exception):
    """Raised when a task hits a blocker requiring human intervention.

    Attributes:
        blocker_type: Category of blocker (login, captcha, verification, etc.)
        message: Human-readable description of what's blocking
        url: The URL where the blocker was detected
        screenshot: Optional base64 screenshot of the blocker
    """

    def __init__(
        self,
        blocker_type: str = "unknown",
        message: str = "Task blocked",
        url: str = "",
        screenshot: str = "",
    ):
        self.blocker_type = blocker_type
        self.message = message
        self.url = url
        self.screenshot = screenshot
        super().__init__(f"[{blocker_type}] {message}")


class CampaignPaused(Exception):
    """Raised when a campaign is paused due to a blocker.

    The executor catches this and waits for a resume signal.
    """

    def __init__(self, campaign_id: str, reason: str = ""):
        self.campaign_id = campaign_id
        self.reason = reason
        super().__init__(f"Campaign {campaign_id} paused: {reason}")
