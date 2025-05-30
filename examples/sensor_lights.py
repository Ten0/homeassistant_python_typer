"""
Basic sensor lights automation.
"""

import appdaemon.plugins.hass.hassapi as hass
from hapt import HomeAssistant


class HallwaySensorLights(hass.Hass):
    timer: str | None

    def initialize(self):
        self.ha = HomeAssistant(self)

        self.light = self.ha.light.hallway_lamp
        self.sensor = self.ha.binary_sensor.hallway_motion_sensor_occupancy

        self.timer = None
        # Track that we asked turn off otherwise we may skip turn_on command while it's turning off (because is_on())
        self.gave_order_to_turn_off = False

        self.sensor.listen_state(self.check_sensor)

        self.check_sensor()

        self.log("Initialized HallwaySensorLights")

    def timer_trigger(self, cb_args: dict[str, object]):
        self.ha.hapt.clear_caches()  # Necessary with native appdaemon triggers
        self.timer = None
        self.set_light()

    def check_sensor(self):
        if self.sensor.is_on() or self.light.is_off():
            self.clear_timer()
        else:
            # light is on but sensor is off
            self.set_timer()
        self.set_light()

    def set_light(self):
        should_be_on = self.sensor.is_on() or self.timer is not None
        if should_be_on:
            if not self.light.is_on() or self.gave_order_to_turn_off:
                self.light.turn_on(brightness=255, kelvin=2202, transition=0.1)
        else:
            if self.light.is_on():
                self.light.turn_off(transition=3)
                self.gave_order_to_turn_off = True

    def set_timer(self):
        if self.timer is None:
            self.timer = self.run_in(self.timer_trigger, 1)

    def clear_timer(self):
        if self.timer is not None:
            self.cancel_timer(self.timer)
            self.timer = None
