# HomeAssistant Python typer

Full-fledged typing for your automation applications. Never see your automations break again.

# What

Run this script to obtain type definitions for all devices available in Home Assistant, which can then be exported to your appdaemon apps folder for use in any appdaemon app.

# Why

## Nocode?

HomeAssistant is a largely no-code platform. This works well for very small automations. However as soon as there are many automations and they are more or less complex, they are a pain to maintain, and/or end up extensively using [Templating](https://www.home-assistant.io/docs/configuration/templating/).

e.g. https://github.com/panhans/HomeAssistant/blob/main/blueprints/automation/panhans/advanced_heating_control.yaml

And I'm at the regret to inform you that... this is not no-code. This is just code. And a terribly painful way to write it, because yaml+jinja is actually not a programming language.

Also if you make the slightest mistake, nothing will catch it until it fails to run the particular automation.

## Code?

Now [AppDaemon](https://appdaemon.readthedocs.io/en/latest/) was built to address this problem: to allow expressing automations in Python rather than Yaml+Jinja when they get really complex (or when you find writing lines of code simpler than clicking left and right in dropdowns.)

Unfortunately it has its shortcomings: namely you lose the nice auto-completion that you get from the UI, where all your entities and actions you can take on them are easily accessible.
Instead you have to enter entity IDs as strings, and hope that whatever function you're calling on them actually exists. In addition, most of home assistant's automations don't pre-exist in the API, so you'll also have to call them by their string names.

Again, if you make mistakes, if you lose devices on the network, or refer non-existing properties, nothing will catch until you try to run them.

## So what?

We're solving AppDaemon's pain point. We introduce a fully typed API, usable within your favorite Python code editor with fully-fledged auto-completion and typing, that contains all your entities, and all functions you can call on available entities.

# How it works

We provide a script which when run on a HomeAssistant instance will generate type definitions for all entities connected to the platform.
```console
homeassistant_python_typer /path/to/hapt.py
```

The generated `hapt.py` file should be placed in your AppDeamon folder. This enables you to use your entities like so:

```python
import appdaemon.plugins.hass.hassapi as hass
from hapt import Entities

class SensorLight(hass.Hass):
    def initialize(self):
        self.entities = Entities(self)
        self.light = self.entities.light.hallway_light # typechecks & autocompletes

        # Not yet improved boilerplate: listen to sensor
        self.listen_state(
            self.on_motion_detected,
            self.entities.binary_sensor.hallway_motion_sensor_occupancy.entity_id,
            new="on",
        )

    async def on_motion_detected(self, entity, attribute, old, new, cb_args):
        # even whether RGB support is available is typechecked!
        await self.light.turn_on(rgb_color="#6F2DA8", brightness=203) 
```

where:
- If you were to typo the name of the light, you'd get a nice big red error message stating that this light doesn't exist in your Home Assistant
- If your light were to not support RGB because it's a light where only the temperature and brightness can be configured, you'd get a nice big red error message stating that `rgb_color` is not available for `hallway_light`'s `turn_on`.
- All functions and function parameters are documented (with the same documentation as in the no-code UI)
- Every function available in Home Assistant is available (because they are introspected by the same API as HomeAssistant uses for its no-code interface)
