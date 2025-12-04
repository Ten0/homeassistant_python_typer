from typing import Any, Tuple
from .dataclasses import *
from .builder import HaptBuilder


def infer_state_superclass(
    builder: HaptBuilder,
    entity_attributes: dict[str, Any],
    entity_id: str,
) -> list[str]:
    extra_superclasses: list[str] = []
    return_type, cast, doc = state_type(entity_attributes, builder, entity_id)

    if return_type is not None:
        superclass_body = f"""
                \"""
                Superclass for entity state that holds return type information and documentation specific to this entity.
                \"""
                def state(
                    self,
                ) -> {return_type}:
                    \"""
                    Retrieve the state of the entity.

                    Returns:
                        The state of the entity.{doc}
                    \"""
                    return {'' if cast is None else f'{cast}('}super().get_state_repeatable_read(){'' if cast is None else ')'}"""
        if superclass_body in builder.classes_per_body:
            extra_superclasses.append(builder.classes_per_body[superclass_body].name)
        else:
            superclass_name = f"state__{len(builder.classes_per_body)}"
            superclass_full_body = (
                f"""
            class {superclass_name}(hapth.Entity):"""
                + superclass_body
            )
            builder.classes_per_body[superclass_body] = EntitySuperclass(
                name=superclass_name, body=superclass_full_body
            )
            extra_superclasses.append(superclass_name)

    return extra_superclasses


def state_type(
    entity_attributes: dict[str, Any],
    builder: HaptBuilder,
    entity_id: str,
) -> Tuple[str | None, str | None, str]:
    return_type: str | None = None
    cast = None
    doc: str = ""

    if entity_id.startswith("counter."):
        if (
            "step" in entity_attributes
            and is_int(entity_attributes["step"])
            and "initial" in entity_attributes
            and is_int(entity_attributes["initial"])
        ):
            return_type = "int"
            cast = "hapth.checked_int"
        else:
            return_type = "int | float"
            cast = "hapth.int_or_float"
    elif entity_id.startswith("number."):
        if number_entity_is_int(entity_attributes):
            return_type = "int"
            cast = "hapth.checked_int"
        else:
            return_type = "int | float"
            cast = "hapth.int_or_float"
    elif entity_id.startswith("select.") and "options" in entity_attributes:
        return_type, doc = enum_type_and_doc(entity_attributes["options"], builder)
    elif any(
        entity_id.startswith(prefix)
        for prefix in ["light.", "binary_sensor.", "input_boolean.", "switch."]
    ):
        return_type = "hapth.OnOff"
        doc += f"""
                    - Returns: `on`/`off`: The state of the entity"""
    elif (
        "state_class" in entity_attributes
        and entity_attributes["state_class"] == "measurement"
    ):
        return_type = "int | float"
        cast = "hapth.int_or_float"
    elif "device_class" in entity_attributes:
        device_class = entity_attributes["device_class"]
        match device_class:
            # https://www.home-assistant.io/integrations/homeassistant/#device-class (click each platform)
            case "enum":
                if "options" in entity_attributes:
                    # I'm not 100% confident that this can't also return "unknown" (or "unavailable" for e.g. lights),
                    # might need to add that to the list (in which case that would probably be None)
                    return_type, doc = enum_type_and_doc(
                        entity_attributes["options"], builder
                    )
                else:
                    print(
                        f"Warning: Entity '{entity_id}' of device class 'enum' is missing 'options' attribute"
                    )
            case (
                "distance"
                | "temperature"
                | "humidity"
                | "pressure"
                | "illuminance"
                | "signal_strength"
                | "battery"
                | "current"
                | "energy"
                | "power"
                | "voltage"
                | "frequency"
            ):
                # I'm not 100% confident that this can't also return "unknown", might need to add that to the list
                # (in which case that would probably be None)
                return_type = "int | float"
                cast = "hapth.int_or_float"
            case "timestamp":
                builder.imports.add("import datetime")
                return_type = "datetime.datetime"
                cast = "datetime.datetime.fromisoformat"
            case _:
                print(
                    f"Warning: Unknown device class '{device_class}' for entity '{entity_id}'"
                )

    if "device_class" in entity_attributes:
        doc += f"""
                    - Device class: `{entity_attributes["device_class"]}`"""
    if "unit_of_measurement" in entity_attributes:
        doc += f"""
                    - Unit: `{entity_attributes['unit_of_measurement']}`"""

    if return_type is None:
        # At least print out the doc and specify that states are always str unless overridden above
        return_type = "str"
    return return_type, cast, doc


def enum_type_and_doc(
    options: list[str],
    builder: HaptBuilder,
):
    return_type = builder.enum_type("state", "State", options)
    line_break = "\n"  # python 3.11 support
    doc = f"""
                        Possible states:
                        - {f'{line_break}                        - '.join((f"`{option}`" for option in options))}"""
    return return_type, doc


def number_entity_is_int(entity_attributes: dict[str, Any]) -> bool:
    return (
        "step" in entity_attributes
        and is_int(entity_attributes["step"])
        and "min" in entity_attributes
        and is_int(entity_attributes["min"])
    )


def is_int(value: Any) -> bool:
    return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
