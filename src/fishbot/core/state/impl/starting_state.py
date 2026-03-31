import time

from ..bot_state import BotState
from ..state_type import StateType


class StartingState(BotState):

    def __init__(self, bot):
        super().__init__(bot)
        self._last_search_log = 0

    def handle(self, screen):

        # 1️⃣ Normal case: detect the fishing spot button
        pos = self.detector.find(screen, "fishing_spot_btn", debug=self.bot.debug_mode)

        if pos:
            self.bot.log(f"[STARTING] ✅ Fishing spot detected at {pos}")
            self.bot.log("[STARTING] Pressing 'F'...")
            time.sleep(0.5)

            self.controller.press_key('f')
            self.bot.log("[STARTING] Entering fishing mode")
            time.sleep(1)

            return StateType.CHECKING_ROD

        # 2️⃣ New: detect if the player is already in fishing mode
        already_fishing = self.detector.find(screen, "level_check", debug=self.bot.debug_mode)

        if already_fishing:
            self.bot.log("[STARTING] 🎣 Already in fishing mode — skipping interaction")
            return StateType.CHECKING_ROD

        # 3️⃣ Fallback: still searching for fishing spot
        current_time = time.time()
        if current_time - self._last_search_log > 2:
            self.bot.log("[STARTING] 🔍 Searching for fishing spot...")
            if self.bot.debug_mode:
                self.bot.log("[STARTING] 💡 Debug enabled")
            self._last_search_log = current_time

        return StateType.STARTING
