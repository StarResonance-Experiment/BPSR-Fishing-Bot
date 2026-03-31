import time

from ..bot_state import BotState
from ..state_type import StateType


class CheckingRodState(BotState):

    def handle(self, screen):
        self.bot.log("[CHECKING_ROD] Checking rod...")

        time.sleep(1)
        if self.detector.find(screen, "broken_rod", debug=self.bot.debug_mode):
            self.bot.log("[CHECKING_ROD] ⚠️  Broken rod! Replacing...")
            self.bot.stats.increment('rod_breaks')
            time.sleep(1)

            self.controller.press_key('m')
            time.sleep(1)
            
            screen = self.detector.capture_screen()
            pos = self.detector.find(screen, "new_rod", debug=self.bot.debug_mode)
            if pos:
                self.controller.move_to(pos[0], pos[1])
                time.sleep(0.5)
                self.controller.move_to(pos[0], pos[1])
                time.sleep(0.5)
                self.controller.click('left')
                time.sleep(1)

                self.bot.log("[CHECKING_ROD] ✅ Rod replaced")
        else:
            time.sleep(1)
            self.bot.log("[CHECKING_ROD] ✅ Rod OK")

        return StateType.CASTING_BAIT
