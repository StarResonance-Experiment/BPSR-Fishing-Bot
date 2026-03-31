import time

from ..bot_state import BotState
from ..state_type import StateType


class PlayingMinigameState(BotState):

    def __init__(self, bot):
        super().__init__(bot)
        self._current_direction = None
        self.switch_delay = 0.5

    def _handle_arrow(self, direction, screen):
        arrow_template = f"{direction}_arrow"
        key_to_press = 'a' if direction == 'left' else 'd'
        key_to_release = 'd' if direction == 'left' else 'a'
        opposite_direction = 'right' if direction == 'left' else 'left'

        if self.detector.find(screen, arrow_template, debug=self.bot.debug_mode):
            if self._current_direction is None:
                self.bot.log(f"[MINIGAME] ▶️ Moving to the {direction} (Holding '{key_to_press}')")
                self.controller.key_down(key_to_press)
                self._current_direction = direction
                time.sleep(self.switch_delay)

            if self._current_direction == opposite_direction:
                self.bot.log(f"[MINIGAME] ◀️ Switching to the {direction} (Releasing '{key_to_release}')")
                self.controller.key_up(key_to_release)
                self._current_direction = None
                time.sleep(self.switch_delay)

    def _on_fish_caught(self) -> StateType:
        self.bot.log("[MINIGAME] 🐟 Fish caught!")
        self.bot.stats.increment('fish_caught')
        self.controller.release_all_controls()
        self._current_direction = None

        if self.config.quick_finish_enabled:
            self.bot.log("[MINIGAME] ⏩ Quick finishing...")
            self.controller.press_key('esc')
            time.sleep(0.5)
            return StateType.STARTING
        return StateType.FINISHING

    def handle(self, screen):
        # Check before processing arrows
        if self.detector.find(screen, "success", debug=self.bot.debug_mode):
            return self._on_fish_caught()

        self._handle_arrow('left', screen)
        self._handle_arrow('right', screen)
        return StateType.PLAYING_MINIGAME