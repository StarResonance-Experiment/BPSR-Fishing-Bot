import time

from ..bot_state import BotState
from ..state_type import StateType


class FinishingState(BotState):

    def __init__(self, bot):
        super().__init__(bot)

    def handle(self, screen):

        pos = self.detector.find(screen, "continue", debug=self.bot.debug_mode)

        if pos:
            self.bot.log("[FINISHING] 🖱️ Clicking 'Continue'...")
            self.controller.move_to(pos[0], pos[1])
            time.sleep(0.5)
            self.controller.move_to(pos[0], pos[1])
            time.sleep(1)
            self.controller.click('left')
		
	    # Count one full fishing attempt
            self.bot.stats.increment("cycles")

            return StateType.CHECKING_ROD

        if self.detector.find(screen, "fishing_spot_btn", debug=self.bot.debug_mode):
            return StateType.STARTING

        return StateType.FINISHING