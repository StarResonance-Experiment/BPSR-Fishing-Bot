from pathlib import Path
from .bot_config import BotConfig
from .paths import PACKAGE_ROOT, ASSETS_PATH, TEMPLATES_PATH


class Config:

    def __init__(self):
        self.bot = BotConfig()

        self.paths = {
            'package_root': PACKAGE_ROOT,
            'assets': ASSETS_PATH,
            'templates': TEMPLATES_PATH
        }

    def get_template_path(self, template_name):
        filename = self.bot.detection.templates.get(template_name)
        if not filename:
            return None

        # 1. External user folder (beside exe / project root) — highest priority
        if self.bot.detection.templates_user_path:
            external = Path(self.bot.detection.templates_user_path) / filename
            if external.exists():
                return external

        # 2. Bundled resolution-specific subfolder (e.g. assets/templates/2560_1440/)
        resolved = Path(self.bot.detection.templates_path) / filename
        if resolved.exists():
            return resolved

        # 3. Flat fallback — legacy / PNGs not in resolution subfolder
        fallback = TEMPLATES_PATH / filename
        if fallback.exists():
            return fallback

        return resolved
