"""
The most basic sensor lights automation.
Equivalent to the HomeAssistant sensor light template
"""

import appdaemon.plugins.hass.hassapi as hass
from hapt import HomeAssistant


class FirstSensorLight(hass.Hass):
    def initialize(self):
        self.ha = HomeAssistant(self)

        self.light = self.ha.light.bed_light
        sensor = self.ha.input_boolean.switch_1

        sensor.listen_state(self.turn_light_on, new="on")
        sensor.listen_state(self.light.turn_off, new="off", duration_s=2)

        self.log("Initialized FirstSensorLight")

    def turn_light_on(self) -> None:
        # We use this intermediate `turn_light_on` function so that we can specify
        # extra parameters to the turn_on call
        self.light.turn_on(brightness_pct=100, color_name="purple")

        # That is not necessary for the turn_off call, because it does not need any
        # additional parameter
