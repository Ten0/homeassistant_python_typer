from typing import Any, Iterable, Tuple


def infer_state_superlcass(
    entity_attributes: dict[str, Any],
    classes_per_body: dict[str, Tuple[str, str]],
    enum_types: dict[Tuple[str, str], Tuple[str, str]],
    entity_id: str,
) -> list[str]:
    extra_superclasses: list[str] = []
    return_type, cast, doc = state_type(entity_attributes, enum_types, entity_id)

    if return_type is not None:
        superclass_body = f"""
                \"""
                Superclass for entity state that holds.
                \"""
                async def state(
                    self,
                ) -> {return_type}:
                    \"""
                    Retrieve the state of the entity.

                    Returns:
                        The state of the entity.{doc}
                    \"""
                    return await {'' if cast is None else f'{cast}('}super().get_state_repeatable_read(){'' if cast is None else ')'}"""
        if superclass_body in classes_per_body:
            extra_superclasses.append(classes_per_body[superclass_body][0])
        else:
            superclass_name = f"state__{len(classes_per_body)}"
            superclass_full_body = (
                f"""
            class {superclass_name}(hapth.Entity):"""
                + superclass_body
            )
            classes_per_body[superclass_body] = (superclass_name, superclass_full_body)
            extra_superclasses.append(superclass_name)

    return extra_superclasses


def state_type(
    entity_attributes: dict[str, Any],
    enum_types: dict[Tuple[str, str], Tuple[str, str]],
    entity_id: str,
) -> Tuple[str | None, str | None, str]:
    return_type: str | None = None
    cast = None
    doc: str = ""
    if "device_class" in entity_attributes:
        device_class = entity_attributes["device_class"]
        match device_class:
            # https://www.home-assistant.io/integrations/homeassistant/#device-class (click each platform)
            case "enum":
                # I'm not 100% confident that this can't also return "unknown" (or "unavailable" for e.g. lights),
                # might need to add that to the list (in which case that would probably be None)
                options = entity_attributes["options"]
                return_type = enum_type(options, enum_types)
                doc = f"""
                        Possible states:
                        - {'\n                        - '.join((f"`{option}`" for option in options))}"""
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
            case _:
                print(
                    f"Warning: Unknown device class '{device_class}' for entity '{entity_id}'"
                )
    if doc == "":
        if "device_class" in entity_attributes:
            doc += f"""
                        - Device class: `{entity_attributes["device_class"]}`"""
        if "unit_of_measurement" in entity_attributes:
            doc += f"""
                        - Unit: `{entity_attributes['unit_of_measurement']}`"""
    if doc != "" and return_type is None:
        # At least print out the doc
        return_type = "Any"
    return return_type, cast, doc


def enum_type(options: list[str], enum_types: dict[Tuple[str, str], Tuple[str, str]]):
    options_iter: Iterable[str] = (repr(option) for option in options)
    field_name = "state"
    type = f"Literal[{", ".join(options_iter)}]"
    if (field_name, type) in enum_types:
        return enum_types[(field_name, type)][0]
    else:
        enum_type_name = f"State{len(enum_types)}"
        enum_types[(field_name, type)] = (
            enum_type_name,
            f"{enum_type_name}: TypeAlias = {type}",
        )
        return enum_type_name
