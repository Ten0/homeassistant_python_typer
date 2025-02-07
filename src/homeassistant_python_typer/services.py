from typing import Any, Iterable, Tuple
import pydoc

from .builder import HaptBuilder
from .dataclasses import *


def service_function_body(
    builder: HaptBuilder,
    service: Service,
    entity_attributes_if_entity: dict[str, Any] | None,
) -> str:
    fields: dict[str, Any] = service.data.get("fields", {})

    # Advanced fields are just fields, flatten that before processing
    for advanced_field, advanced_field_data in fields.pop(
        "advanced_fields", {"fields": {}}
    )["fields"].items():
        # Prioritize non-advanced fields
        if advanced_field not in fields:
            fields[advanced_field] = advanced_field_data

    service_function_body = f"""
                async def {service.name}(
                    self,"""
    service_data_dict = ""
    parameters_doc = ""
    for field_name, field_data in fields.items():
        # Make sure the field should actually be active for this particular instance,
        # based on filter
        if not field_is_available_for_entity(field_data, entity_attributes_if_entity):
            continue

        # It should indeed be active
        selector = field_data.get("selector", {})
        field_type_and_default, field_value_construction = choose_field_type(
            field_name,
            selector,
            entity_attributes_if_entity=entity_attributes_if_entity,
            service=service,
            builder=builder,
        )

        sanitized_field_name = (
            f"{field_name}_" if field_name in pydoc.Helper.keywords else field_name
        )

        is_multiple = all(
            (
                isinstance(v, dict) and v.get("multiple", False)
                for v in selector.values()
            )  # pyright: ignore[reportUnknownArgumentType]
        )
        required = field_data.get("required", False)

        if field_value_construction is None:
            field_value_construction = sanitized_field_name
        else:
            if is_multiple:
                field_value_construction = f"[{field_value_construction.replace('#FIELD_NAME#', f'{field_name}_e')} for {field_name}_e in {sanitized_field_name}]"
            else:
                field_value_construction = field_value_construction.replace(
                    "#FIELD_NAME#", sanitized_field_name
                )
            if not required:
                field_value_construction = f"{field_value_construction} if {sanitized_field_name} is not None else None"

        if is_multiple:
            field_type_and_default = f"list[{field_type_and_default}]"
        if not required:
            field_type_and_default = f"{field_type_and_default} | None = None"

        if service_data_dict == "":
            # First field, prevent non-keyword arguments
            service_function_body += f"""
                    *,"""
        service_function_body += f"""
                    {sanitized_field_name}: {field_type_and_default},"""
        service_data_dict += f"""
                            "{field_name}": {field_value_construction},"""
        parameters_doc += f"""
                    `{sanitized_field_name}` (`{field_type_and_default}`{"" if required else ", optional"})"""
        description = field_data.get("description", field_data.get("name", ""))
        if description:
            parameters_doc += f"""
                        {field_data.get("description", field_data.get("name", ""))}"""
        parameters_doc += "\n"
    if parameters_doc.endswith("\n"):
        parameters_doc = parameters_doc[:-1]
    if service_data_dict != "":
        service_data_dict += """
                        """
    service_function_body += f"""
                ) -> None:
                    \"""
                    {service.data.get("description", service.data.get("name", ""))}

                    Parameters
                    ----------{parameters_doc}
                    \"""
                    await self{"._hapt" if entity_attributes_if_entity is None else ""}.call(
                        "{service.domain}",
                        "{service.name}",
                        {{{service_data_dict}}},
                    )"""

    return service_function_body


def infer_services_superclasses(
    builder: HaptBuilder,
    domain: str,
    entity_attributes: dict[str, Any],
    per_entity_domain_services: dict[str, list[Service]],
) -> list[str]:
    extra_superclasses: list[str] = []
    for service in per_entity_domain_services.get(domain, []):
        # At this point we already know our entity is compatible with the service
        superclass_body = service_function_body(
            builder=builder,
            service=service,
            entity_attributes_if_entity=entity_attributes,
        )

        if superclass_body in builder.classes_per_body:
            extra_superclasses.append(builder.classes_per_body[superclass_body].name)
        else:
            superclass_name = f"service__{service.domain}__{service.name}__{len(builder.classes_per_body)}"
            superclass_full_body = (
                f"""
            class {superclass_name}(hapth.Entity):"""
                + superclass_body
            )
            builder.classes_per_body[superclass_body] = ServiceClass(
                name=superclass_name, body=superclass_full_body
            )
            extra_superclasses.append(superclass_name)

    return extra_superclasses


def choose_field_type(
    field_name: str,
    selector: dict[str, Any],
    entity_attributes_if_entity: dict[str, Any] | None,
    builder: HaptBuilder,
    service: Service,
) -> Tuple[str, str | None]:
    "returns type and optionally field value construction override"

    selector_is_object = lambda: all(
        map(lambda v: v == "object", selector)
    )  # unspecified type
    if "text" in selector:
        if (
            entity_attributes_if_entity is not None
            and service.domain == "select"
            and "options" in entity_attributes_if_entity
        ):
            return (
                options_enum_type(
                    field_name, entity_attributes_if_entity["options"], builder
                ),
                None,
            )
        return "str", None
    elif "number" in selector:
        number = selector["number"]
        if (
            isinstance(number.get("step", 1), int)
            and not number.get("unit_of_measurement") == "seconds"
        ):
            return "int", None
        return "float", None
    elif "boolean" in selector:
        return "bool", None
    elif "date" in selector or "datetime" in selector:
        # TODO probably can use a better type here?
        return "str", None
    elif "select" in selector:
        select = selector["select"]
        return (
            options_enum_type(field_name, select["options"], builder),
            None,
        )
    elif "entity" in selector:
        # TODO probably replace with a {Domain}Entity type (that is added to the available supertypes
        # if anything references it here or among existing entities)
        # Or create a superclass for the field that should be given to each entity that can be used for this field
        # (Advantage of this second solution is this can take into account `supported_features` as well for e.g.
        # `weather.get_forecasts`)
        return "hapth.Entity", "#FIELD_NAME#.entity_id"
    elif "color_rgb" in selector or (
        field_name == "rgb_color" and selector_is_object()
    ):
        return (
            "Tuple[int, int, int] | list[int] | str",
            f"hapth.rgb_color(#FIELD_NAME#)",
        )
    elif "color_temp" in selector:
        return "int", None
    elif "color_xy" in selector or (field_name == "xy_color" and selector_is_object()):
        return "Tuple[float, float]", None
    elif "color_hs" in selector or (field_name == "hs_color" and selector_is_object()):
        return "Tuple[float, float]", None
    else:
        print(
            f"Warning: Unknown field type for {service.domain}/{service.name} - {field_name}: {selector}"
        )
        return "Any", None


def options_enum_type(
    field_name: str,
    options: Iterable[str | dict[str, Any]],
    builder: HaptBuilder,
) -> str:
    "Finds or create the necessary enum in enum_types, and returns its name"
    return builder.enum_type(field_name, f"Options{field_name.title()}", options)


def field_is_available_for_entity(
    field_data: dict[str, Any], entity_attributes_if_entity: dict[str, Any] | None
) -> bool:
    if "filter" in field_data:
        if entity_attributes_if_entity is not None:
            entity_attributes = entity_attributes_if_entity
            filter = field_data["filter"]
            if "supported_features" in filter:
                supported_features = filter["supported_features"]
                if not any(
                    (
                        entity_attributes.get("supported_features", 0)
                        & supported_feature_filter
                        == supported_feature_filter
                    )
                    for supported_feature_filter in supported_features
                ):
                    return False
            if "attribute" in filter:
                for attribute_name, attribute_value in filter["attribute"].items():
                    if attribute_name not in entity_attributes:
                        return False
                    if not entity_has_attribute(
                        entity_attributes[attribute_name], attribute_value
                    ):
                        return False
    return True


def entity_has_attribute(entity_attribute: Any, attribute_filter: Any) -> bool:
    if isinstance(attribute_filter, list):
        return any(
            (
                entity_has_attribute(entity_attribute, value)
                for value in attribute_filter
            )
        )
    if isinstance(entity_attribute, list):
        return any(
            (
                entity_has_attribute(value, attribute_filter)
                for value in entity_attribute
            )
        )
    return entity_attribute == attribute_filter


def per_entity_domain_services(
    hm_services: list[dict[str, Any]],
) -> dict[str, list[Service]]:
    """
    Go from [{service_domain: str, services: {service_name: {target: {entity: [{entity_domain}]}}}}]
    to
    {entity_domain: [(service_domain, service_name, service_data)]}
    """
    per_domain_services: dict[str, list[Service]] = {}
    for service_domain in hm_services:
        service_domain_name = service_domain["domain"]
        for service_name, service_data in service_domain["services"].items():
            if target := service_data.get("target"):
                if entity := target.get("entity"):
                    service = Service(
                        domain=service_domain_name,
                        name=service_name,
                        data=service_data,
                    )
                    for entity_filter in entity:
                        if entity_filter_domain := entity_filter.get("domain"):
                            for filter_domain in entity_filter_domain:
                                if per_domain_services.get(filter_domain) is None:
                                    per_domain_services[filter_domain] = []
                                per_domain_services[filter_domain].append(service)
    return per_domain_services
