from typing import Any, Iterable, Tuple


def infer_services_superclasses(
    domain: str,
    entity_attributes: dict[str, Any],
    classes_per_body: dict[str, Tuple[str, str]],
    hm_services: dict[str, list[Tuple[str, str, Any]]],
    enum_types: dict[Tuple[str, str], Tuple[str, str]],
) -> list[str]:
    extra_superclasses: list[str] = []
    for service_domain_name, service_name, service_data in hm_services.get(domain, []):
        # At this point we already know our entity is compatible with the service
        fields: dict[str, Any] = service_data.get("fields", {})

        # Advanced fields are just fields, flatten that before processing
        for advanced_field, advanced_field_data in fields.pop(
            "advanced_fields", {"fields": {}}
        )["fields"].items():
            # Prioritize non-advanced fields
            if advanced_field not in fields:
                fields[advanced_field] = advanced_field_data

        superclass_body = f"""
                async def {service_name}(
                    self,"""
        service_data_dict = ""
        for field_name, field_data in fields.items():
            field_type_and_default, field_value_construction = choose_field_type(
                field_name, field_data["selector"], enum_types=enum_types
            )
            required = field_data.get("required", False)
            if field_value_construction is None:
                field_value_construction = field_name
            elif not required:
                field_value_construction = (
                    f"{field_value_construction} if {field_name} is not None else None"
                )
            if not required:
                field_type_and_default = f"{field_type_and_default} | None = None"
            if service_data_dict == "":
                # First field, prevent non-keyword arguments
                superclass_body += f"""
                    *,"""
            superclass_body += f"""
                    {field_name}: {field_type_and_default},"""
            service_data_dict += f"""
                            "{field_name}": {field_value_construction},"""
        if service_data_dict != "":
            service_data_dict += """
                        """
        superclass_body += f"""
                ) -> None:
                    await self.call(
                        "{service_domain_name}",
                        "{service_name}",
                        {{{service_data_dict}}},
                    )"""

        if superclass_body in classes_per_body:
            extra_superclasses.append(classes_per_body[superclass_body][0])
        else:
            superclass_name = f"service__{service_domain_name}__{service_name}__{len(classes_per_body)}"
            superclass_full_body = (
                f"""
            class {superclass_name}(hapth.Entity):"""
                + superclass_body
            )
            classes_per_body[superclass_body] = (superclass_name, superclass_full_body)
            extra_superclasses.append(superclass_name)
    return extra_superclasses


def choose_field_type(
    field_name: str,
    selector: dict[str, Any],
    enum_types: dict[Tuple[str, str], Tuple[str, str]],
) -> Tuple[str, str | None]:
    selector_is_object = lambda: all(
        map(lambda v: v == "object", selector)
    )  # unspecified type
    if "text" in selector:
        return "str", None
    elif "number" in selector:
        if isinstance(selector["number"].get("step", 1), int):
            return "int", None
        return "float", None
    elif "boolean" in selector:
        return "bool", None
    elif "date" in selector or "datetime" in selector:
        # TODO probably can use a better type here?
        return "str", None
    elif "select" in selector:
        select = selector["select"]
        options = select["options"]
        options: Iterable[str] = (
            repr(option["value"]) if isinstance(option, dict) else repr(option)  # type: ignore[reportArgumentType]
            for option in options
        )
        type = f"Literal[{", ".join(options)}]"
        if (field_name, type) in enum_types:
            return enum_types[(field_name, type)][0], None
        else:
            enum_type_name = f"Options{field_name.title()}{len(enum_types)}"
            enum_types[(field_name, type)] = (
                enum_type_name,
                f"{enum_type_name}: TypeAlias = {type}",
            )
            return enum_type_name, None
    elif "entity" in selector:
        # TODO probably replace with a {Domain}Entity type (that is added to the available supertypes
        # if anything references it here or among existing entities)
        # LightEntity would be special-cased to inherit LightEntityExt
        # transformator would not be None, but instead be `(lambda x: x.entity_id)`
        return "hapth.Entity", f"{field_name}.entity_id"
    elif "color_rgb" in selector or (
        field_name == "rgb_color" and selector_is_object()
    ):
        return (
            "Tuple[int, int, int] | list[int] | str",
            f"hapth.rgb_color({field_name})",
        )
    elif "color_temp" in selector:
        return "int", None
    elif "color_xy" in selector or (field_name == "xy_color" and selector_is_object()):
        return "Tuple[float, float]", None
    elif "color_hs" in selector or (field_name == "hs_color" and selector_is_object()):
        return "Tuple[float, float]", None
    else:
        print(f"Warning: Unknown field type for {field_name}: {selector}")
        return "Any", None


def per_entity_domain_services(
    hm_services: list[dict[str, Any]],
) -> dict[str, list[Tuple[str, str, Any]]]:
    """
    Go from [{service_domain: str, services: {service_name: {target: {entity: [{entity_domain}]}}}}]
    to
    {entity_domain: [(service_domain, service_name, service_data)]}
    """
    per_domain_services = {}
    for service_domain in hm_services:
        service_domain_name = service_domain["domain"]
        for service_name, service_data in service_domain["services"].items():
            if target := service_data.get("target"):
                if entity := target.get("entity"):
                    for entity_filter in entity:
                        if entity_filter_domain := entity_filter.get("domain"):
                            for filter_domain in entity_filter_domain:
                                if per_domain_services.get(filter_domain) is None:
                                    per_domain_services[filter_domain] = []
                                per_domain_services[filter_domain].append(
                                    (service_domain_name, service_name, service_data)
                                )
    return per_domain_services
