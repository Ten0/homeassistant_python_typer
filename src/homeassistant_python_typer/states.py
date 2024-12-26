from typing import Any, Iterable, Tuple


def infer_state_superlcass(
    entity_attributes: dict[str, Any],
    classes_per_body: dict[str, Tuple[str, str]],
    enum_types: dict[Tuple[str, str], Tuple[str, str]],
) -> list[str]:
    extra_superclasses: list[str] = []
    if (
        "device_class" in entity_attributes
        and entity_attributes["device_class"] == "enum"
    ):
        options = entity_attributes["options"]
        state_return_type = enum_type(options, enum_types)
        superclass_body = f"""
                \"""
                Superclass for entity state that holds.
                \"""
                async def state(
                    self,
                ) -> {state_return_type}:
                    \"""
                    Retrieve the state of the entity.

                    Returns:
                        The state of the entity.
                        Possible states:
                        - {'\n                        - '.join((f"`{option}`" for option in options))}
                    \"""
                    return await super().get_state_repeatable_read()"""
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
