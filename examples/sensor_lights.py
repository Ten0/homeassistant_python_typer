"""
Sensor lights automation.

Features:
- Night mode
- Differing light levels, colors and stay-on duration for night and day
"""

from datetime import time
import appdaemon.plugins.hass.hassapi as hass
from hapt import Entities

night_start = time(23)
night_end = time(8)


class HallwaySensorLights(hass.Hass):
    timer: str | None

    def initialize(self):
        self.entities = Entities(self)

        self.light = self.entities.light.hallway_lamp
        self.sensor = self.entities.binary_sensor.hallway_motion_sensor_occupancy

        self.timer = None
        # Track that we asked turn off otherwise we may skip turn_on command while it's turning off (because is_on())
        self.gave_order_to_turn_off = False

        self.sensor.listen_state(self.check_sensor)
        self.run_daily(self.check_light_trigger, night_start)  # day mode to night mode
        self.run_daily(self.check_light_trigger, night_end)  # night mode to day mode

        self.check_sensor()

        self.log("Initialized HallwaySensorLights")

    def timer_trigger(self, cb_args: dict[str, object]):
        self.entities.hapt.clear_caches()  # Necessary with native appdaemon triggers
        self.timer = None
        self.set_light()

    def check_light_trigger(self, cb_args: dict[str, object]):
        self.entities.hapt.clear_caches()  # Necessary with native appdaemon triggers
        self.set_light()

    def check_sensor(self):
        if self.sensor.is_on() or self.light.is_off():
            self.clear_timer()
        elif self.light.is_on():
            self.set_timer()
        self.set_light()

    def set_light(self):
        should_be_on = self.sensor.is_on() or self.timer is not None
        if should_be_on:
            if not self.light.is_on() or self.gave_order_to_turn_off:
                if self.is_night():
                    # Let's not get super bright light when going to the bathroom at night
                    self.light.turn_on(
                        brightness=46, xy_color=(0.692, 0.295), transition=0.1
                    )
                else:
                    self.light.turn_on(brightness=255, kelvin=2202, transition=0.1)
                self.gave_order_to_turn_off = False
        else:
            if self.light.is_on():
                self.light.turn_off(transition=3)
                self.gave_order_to_turn_off = True

    def set_timer(self):
        if self.timer is None:
            self.timer = self.run_in(
                self.timer_trigger, 4 * 60 if self.is_night() else 2 * 60
            )

    def clear_timer(self):
        if self.timer is not None:
            self.cancel_timer(self.timer)
            self.timer = None

    def is_night(self) -> bool:
        time = self.time()
        return time >= night_start or time < night_end
