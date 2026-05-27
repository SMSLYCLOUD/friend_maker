from app.platforms.skyvern_adapter import SkyvernAdapter

def get_platform_adapter(platform_name, page=None):
    return SkyvernAdapter(platform=platform_name)
