from app.platforms.skyvern_adapter import SkyvernAdapter
from app.platforms.camoufox_adapter import CamoufoxAdapter

# Platforms that use Camoufox (anti-detection) instead of Skyvern
CAMOUFOX_PLATFORMS = {"tiktok"}

def get_platform_adapter(platform_name, page=None):
    if platform_name.lower() in CAMOUFOX_PLATFORMS:
        return CamoufoxAdapter(platform=platform_name)
    return SkyvernAdapter(platform=platform_name)
