from typing import Any
from .builder import HaptBuilder
from .dataclasses import *
from .services import service_function_body


def infer_headless_services(builder: HaptBuilder, hm_services: Any) -> None:
    for service_domain in hm_services:
        service_domain_name = service_domain["domain"]
        for service_name, service_data in service_domain["services"].items():
            target = service_data.get("target", {})
            if "entity" not in target:
                # This is a headless service, we can add it to the builder
                if service_domain_name not in builder.domains:
                    builder.domains[service_domain_name] = Domain(
                        entities=[], services=[], entities_names=set()
                    )
                domain = builder.domains[service_domain_name]
                domain.services.append(
                    ServiceEndpoint(
                        declaration=service_function_body(
                            builder=builder,
                            service=Service(
                                domain=service_domain_name,
                                name=service_name,
                                data=service_data,
                            ),
                            entity_attributes_if_entity=None,
                            field_names_on_same_class=domain.entities_names,  # This relies on entities being added first
                        )
                    )
                )
