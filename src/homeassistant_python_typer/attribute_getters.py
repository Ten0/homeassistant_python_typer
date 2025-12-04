from typing import Any
from .dataclasses import *
from .builder import HaptBuilder
from .helpers import sanitize_ident, sanitize_for_ident


def infer_attributes_superclasses(
    builder: HaptBuilder,
    entity_attributes: dict[str, Any],
) -> list[str]:
    extra_superclasses: list[str] = []

    for attribute_key in entity_attributes:
        attribute_options_key = f"{attribute_key}s"
        if (
            isinstance(entity_attributes[attribute_key], str)
            and attribute_options_key in entity_attributes
            and isinstance(entity_attributes[attribute_options_key], list)
            and isinstance(entity_attributes[attribute_options_key][0], str)
            and (
                entity_attributes[attribute_key]
                in entity_attributes[attribute_options_key]
            )
        ):
            return_type, doc = enum_type_and_doc(
                attribute_key,
                entity_attributes[attribute_options_key],
                builder,
            )
            superclass_body = f"""
                \"""
                Superclass that adds getter for attribute, with return type information and documentation specific to this entity.
                \"""
                def {sanitize_ident(attribute_key)}(
                    self,
                ) -> {return_type}:
                    \"""
                    Retrieve the `{attribute_key}` attribute of the entity.

                    Returns:
                        The `{attribute_key}` attribute of the entity.{doc}
                    \"""
                    return super().get_state_repeatable_read({repr(attribute_key)})"""
            if superclass_body in builder.classes_per_body:
                extra_superclasses.append(
                    builder.classes_per_body[superclass_body].name
                )
            else:
                superclass_name = f"attribute__{sanitize_for_ident(attribute_key)}__{len(builder.classes_per_body)}"
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


def enum_type_and_doc(
    attribute_name: str,
    options: list[str],
    builder: HaptBuilder,
):
    return_type = builder.enum_type(
        attribute_name, f"Attribute{attribute_name.title()}", options
    )
    line_break = "\n"  # python 3.11 support
    doc = f"""
                        Possible values:
                        - {f'{line_break}                        - '.join((f"`{option}`" for option in options))}"""
    return return_type, doc
