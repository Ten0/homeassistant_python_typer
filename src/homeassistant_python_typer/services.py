from typing import Any, Tuple

superclass_counter = 1


def infer_services_superclasses(
    domain: str,
    entity_attributes: dict[str, Any],
    classes_per_body: dict[str, Tuple[str, str]],
    hm_services: dict[str, list[Tuple[str, str, Any]]],
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
            field_type_and_default = choose_field_type(field_data)
            required = field_data.get("required", False)
            if not required:
                field_type_and_default = f"{field_type_and_default} | None = None"
            if service_data_dict == "":
                # First field, prevent non-keyword arguments
                superclass_body += f"""
                    *,"""
            superclass_body += f"""
                    {field_name}: {field_type_and_default},"""
            service_data_dict += f"""
                            "{field_name}": {field_name},"""
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
            global superclass_counter
            superclass_name = (
                f"service__{service_domain_name}__{service_name}__{superclass_counter}"
            )
            superclass_counter += 1
            superclass_full_body = (
                f"""
            class {superclass_name}(hapth.Entity):"""
                + superclass_body
            )
            classes_per_body[superclass_body] = (superclass_name, superclass_full_body)
            extra_superclasses.append(superclass_name)
    return extra_superclasses


def choose_field_type(selector: dict[str, Any]) -> str:
    return "str"


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
