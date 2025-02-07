"""
Presence-based thermostat control automation.

Features:
- Different heating temperatures based on presence and night mode
- Detect presence based on phone device tracker
- Detect night based on time & whether phones are plugged to the wall
- Turn on heating if haven't left the house towards work some time after unplugging phones
- "Heat now" switch to bypass presence detection and start heating right away (automatically turns off)
"""

import appdaemon.plugins.hass.hassapi as hass
from hapt import HomeAssistant
import hapt
import datetime
from datetime import time
from typing import assert_never
from dataclasses import dataclass

NIGHT_START = time(23)
NIGHT_END = time(8)
HEAT_NOW_SWITCH_TIME_SECONDS = 60 * 60  # 1 hour
HEAT_AFTER_UNPLUGGED_MINUTES = 30

HEATING_TEMPERATURE_HEAT = 21.0
HEATING_TEMPERATURE_NIGHT = 14.0
HEATING_TEMPERATURE_AWAY = 5.0


class ThermostatControl(hass.Hass):
    def initialize(self):
        self.ha = HomeAssistant(self)

        self.thermostat = self.ha.climate.livingroom_thermostat
        self.persons = (
            Person(
                app=self,
                phone_device_tracker=self.ha.device_tracker.person1_phone,
                phone_battery_state=self.ha.sensor.person1_phone_battery_state,
            ),
            Person(
                app=self,
                phone_device_tracker=self.ha.device_tracker.person2_phone,
                phone_battery_state=self.ha.sensor.person2_phone_battery_state,
            ),
        )
        self.heat_now_switch = self.ha.input_boolean.heat_now

        for person in self.persons:
            person.phone_device_tracker.listen_state(self.check)
            person.phone_battery_state.listen_state(self.check)

        self.run_daily(
            self.appdaemon_native_trigger, NIGHT_START
        )  # day mode to night mode
        self.run_daily(
            self.appdaemon_native_trigger, NIGHT_END
        )  # night mode to day mode
        self.heat_now_switch.listen_state(self.check)

        # Listen to heat now switch being on for a while - this is not ideal because AppDaemon doesn't take into account
        # the `last_changed` attribute of the switch, but ideally that should be changed in AppDaemon itself, and
        # at least this is very simple.
        self.heat_now_switch.listen_state(
            self.heat_now_switch_on_for_long_enough_to_turn_off,
            new="on",
            duration_s=HEAT_NOW_SWITCH_TIME_SECONDS,
        )

        heating_to_temperature = self.check()

        self.log(
            f"Initialized ThermostatControl, target temperature: {heating_to_temperature} C"
        )

    def appdaemon_native_trigger(self, cb_args: dict[str, object]):
        "Useful for direct AppDaemon triggers (e.g. run_daily or run_in)"
        self.ha.hapt.clear_caches()  # Necessary with native appdaemon triggers
        self.check()

    def check(self):
        should_heat_to_temperature = max(
            (person.should_heat_to_temperature() for person in self.persons)
        )

        # If we pressed the heat_now switch in the last hour, we want to heat to at least 21.0 C
        if self.heat_now_switch.is_on():
            should_heat_to_temperature = max(
                HEATING_TEMPERATURE_HEAT, should_heat_to_temperature
            )

        if self.thermostat.temperature() != should_heat_to_temperature:
            self.log(f"Setting thermostat to {should_heat_to_temperature} C")
            self.thermostat.set_temperature(temperature=should_heat_to_temperature)

        return should_heat_to_temperature

    def heat_now_switch_on_for_long_enough_to_turn_off(self):
        # Effectively this means if we press the "heat now" switch, it will heat for the next hour regardless
        # of phones states.
        self.log("Completed heat_now_switch timer")
        self.heat_now_switch.turn_off()
        self.check()

    def is_night(self) -> bool:
        cache = self.ha.hapt.state_cache
        if "thermostatcontrol__is_night" in cache:
            return cache["thermostatcontrol__is_night"]
        time = self.time()
        ret = time >= NIGHT_START or time < NIGHT_END
        cache["thermostatcontrol__is_night"] = ret
        return ret

    def now(self) -> datetime.datetime:
        if "thermostatcontrol__now" in self.ha.hapt.state_cache:
            return self.ha.hapt.state_cache["thermostatcontrol__now"]
        now = self.datetime(aware=True)
        self.ha.hapt.state_cache["thermostatcontrol__now"] = now
        return now


@dataclass
class Person:
    app: ThermostatControl

    phone_device_tracker: (
        hapt.entity__device_tracker__person1_phone
        | hapt.entity__device_tracker__person2_phone
    )
    phone_battery_state: (
        hapt.entity__sensor__person1_phone_battery_state
        | hapt.entity__sensor__person2_phone_battery_state
    )

    is_plugged_since_night: bool = False
    still_here_after_unplug_timer: str | None = None

    def should_heat_to_temperature(self) -> float:
        if self.is_phone_plugged():
            if self.app.is_night() or self.still_here_after_unplug_timer is not None:
                self.is_plugged_since_night = True
            self.clear_still_here_timer()
        elif self.is_plugged_since_night or (
            self.app.is_night()
            and self.app.thermostat.temperature() == HEATING_TEMPERATURE_NIGHT
            and self.phone_battery_state.last_changed()
            > self.app.now() - datetime.timedelta(minutes=HEAT_AFTER_UNPLUGGED_MINUTES)
        ):
            # The "if last changed is less than 30min ago then also start unplug timer" is meant to recover state
            # on AppDaemon reboot and only works because if !is_plugged then any previous state was plugged
            self.set_still_here_timer()
            self.is_plugged_since_night = False

        if not self.is_home():
            return HEATING_TEMPERATURE_AWAY
        if (
            self.is_plugged_since_night
            or self.still_here_after_unplug_timer is not None
        ):
            return HEATING_TEMPERATURE_NIGHT
        return HEATING_TEMPERATURE_HEAT

    def is_home(self) -> bool:
        return self.phone_device_tracker.get_state_repeatable_read() == "home"

    def is_phone_plugged(self) -> bool:
        """
        Returns whether phones are plugged to a charger.
        This probably means we are in bed (or about to be).
        """
        entity_state = self.phone_battery_state.state()
        match entity_state:
            case "charging" | "full" | "not_charging":
                # not_charging means plugged but reached threshold of max battery amount to charge and stopped charging
                # Avoiding to full-charge is good for battery longevity
                return True
            case "discharging":
                return False
            case _:
                assert_never(entity_state)

    def set_still_here_timer(self):
        if self.still_here_after_unplug_timer is None:
            delay_s = 30 * 60

            def timer_callback(cb_args: dict[str, object]):
                self.still_here_after_unplug_timer = None
                self.app.log(
                    f"Completed still_here_after_unplug_timer for {self.phone_battery_state.entity_id}"
                )
                self.app.appdaemon_native_trigger(cb_args)

            self.still_here_after_unplug_timer = self.app.run_in(
                timer_callback,
                delay_s,
            )
            self.app.log(
                f"Set still_here_after_unplug_timer for {self.phone_battery_state.entity_id}"
            )

    def clear_still_here_timer(self):
        if self.still_here_after_unplug_timer is not None:
            self.app.cancel_timer(self.still_here_after_unplug_timer)
            self.still_here_after_unplug_timer = None
            self.app.log(
                f"Cleared still_here_after_unplug_timer for {self.phone_battery_state.entity_id}"
            )
