from typing import Any

from .builder import HaptBuilder
from .services import infer_services_superclasses, per_entity_domain_services
from .states import infer_state_superclass
from .helpers import retab
from .dataclasses import *


def infer_entities(
    builder: HaptBuilder,
    hm_entities: Any,
    hm_services: Any,
    generate_as_async: bool,
) -> None:
    per_entity_domain_services_ = per_entity_domain_services(hm_services=hm_services)
    for entity in hm_entities:
        entity_id: str = entity["entity_id"]
        domain, entity_name = entity_id.split(".", 1)
        entity_attributes = entity["attributes"]

        superclass = "Entity"
        match domain:
            case "light" | "binary_sensor" | "input_boolean" | "switch":
                superclass = (
                    "OnOffState" if not generate_as_async else "OnOffStateAsync"
                )
            case "input_button":
                superclass = (
                    "InputButton" if not generate_as_async else "InputButtonAsync"
                )
            case (
                "climate"
            ) if "temperature" in entity_attributes and "current_temperature" in entity_attributes:
                superclass = "Climate" if not generate_as_async else "ClimateAsync"
            case _:
                # match can't be expressions in Python :(
                pass

        superclasses = ", ".join(
            infer_state_superclass(
                builder=builder,
                entity_attributes=entity_attributes,
                entity_id=entity_id,
            )
            + infer_services_superclasses(
                builder=builder,
                domain=domain,
                entity_attributes=entity_attributes,
                per_entity_domain_services=per_entity_domain_services_,
            )
            + [f"hapth.{superclass}"]
        )

        entity_friendly_name: str | None = (entity.get("attributes", {})).get(
            "friendly_name", None
        )

        class_name = f"entity__{domain}__{entity_name}"
        entity_body = retab(
            f"""
            class {class_name}({superclasses}):
                \"""
                `{entity_id}`{f": {entity_friendly_name}" if entity_friendly_name else ""}
                \"""
                pass""".lstrip(
                "\n"
            ),
            1,
        )
        builder.entities.append(Entity(name=entity_name, declaration_body=entity_body))

        entity_type_in_domain = class_name
        if domain not in builder.domains:
            builder.domains[domain] = Domain(entities=[], services=[])
        builder.domains[domain].entities.append(
            DomainEntity(
                name=entity_name,
                type_name=entity_type_in_domain,
                friendly_name=entity_friendly_name,
            )
        )
