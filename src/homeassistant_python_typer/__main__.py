from typing import Tuple
import requests
import json
import os
import sys

from .services import infer_services_superclasses, per_entity_domain_services


def main():
    # Read from env variables
    ha_url = os.environ["HOMEASSISTANT_URL"]
    ha_token = os.environ["HOMEASSISTANT_TOKEN"]

    # Make sure output filename was provided as an argument
    if len(sys.argv) < 2:
        print("Usage: homeassistant_python_typer /path/to/hapt.py")
        sys.exit(1)

    # Read the output filename from the arguments
    output_filename = sys.argv[1]

    client = HomeAssistantClient(ha_url, ha_token)

    hm_entities = client.get("states")
    hm_services = client.get("services")

    if "-d" in sys.argv:
        # For debugging
        with open("entities.json", "w") as entities_file:
            entities_file.write(json.dumps(hm_entities, indent=4))
        with open("services.json", "w") as services_file:
            services_file.write(json.dumps(hm_services, indent=4))

    # Per-domain lookup table of services
    hm_services_dict = per_entity_domain_services(hm_services)

    # body of the class, class name
    classes_per_body: dict[str, Tuple[str, str]] = {}

    # entity id, body
    entities: list[Tuple[str, str]] = []

    # domain name, [(entity name, entity type in domain, entity doc)]
    domains: dict[str, list[Tuple[str, str, str | None]]] = {}

    # (field name, type) -> (type alias name, type alias declaration)
    enum_types: dict[Tuple[str, str], Tuple[str, str]] = {}

    for entity in hm_entities:
        entity_id: str = entity["entity_id"]
        domain, entity_name = entity_id.split(".", 1)

        superclass = "Light" if domain == "light" else "Entity"
        superclasses = ", ".join(
            infer_services_superclasses(
                domain=domain,
                entity_attributes=entity["attributes"],
                classes_per_body=classes_per_body,
                hm_services=hm_services_dict,
                enum_types=enum_types,
            )
            + [f"hapth.{superclass}"]
        )

        entity_friendly_name = (entity.get("attributes", {})).get("friendly_name", None)

        class_name = f"entity__{domain}__{entity_name}"
        entity_body = retab(
            f"""
            class {class_name}({superclasses}):
                \"""
                `{entity_id}`: {entity_friendly_name}
                \"""
                pass""".lstrip(
                "\n"
            ),
            1,
        )
        entities.append((entity_name, entity_body))

        entity_type_in_domain = class_name
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(
            (
                entity_name,
                entity_type_in_domain,
                entity_friendly_name,
            )
        )

    services_classes = [
        (class_name, body) for _, (class_name, body) in classes_per_body.items()
    ]
    services_classes.sort(key=lambda x: x[0])  # sort by name for consistency
    entities.sort(key=lambda x: x[0])  # sort by name for consistency
    domains_classes = [
        (domain_name, domain_entities)
        for domain_name, domain_entities in domains.items()
    ]
    domains_classes.sort(key=lambda x: x[0])  # sort by name for consistency
    for _, domain_entities in domains_classes:
        domain_entities.sort(key=lambda x: x[0])

    enum_declarations_body = "\n".join((value for _, value in enum_types.values()))
    services_classes_body = "\n\n".join(
        (value for _, value in services_classes)
    ).lstrip("\n")
    entities_classes_body = "\n\n".join((value for _, value in entities))
    domains_classes_body = ""
    domains_init_body = ""
    for domain_name, domain_entities in domains_classes:
        domain_name_in_title_case = domain_name.title()
        if domains_classes_body != "":
            domains_classes_body += "\n"
        domains_classes_body += f"""
        class {domain_name_in_title_case}Domain(hapth.Domain):
            def __init__(self, hapt: hapth.HaptSharedState):
                super().__init__(hapt, "{domain_name}")\n\n""".lstrip(
            "\n"
        )
        for entity_name, entity_type_in_domain, entity_docstring in domain_entities:
            entity_docstring = (
                ("\n" + repr(entity_docstring)) if entity_docstring else ""
            )
            domains_classes_body += (
                tab(
                    f"{entity_name}: {entity_type_in_domain}{entity_docstring}",
                    3,
                )
                + "\n\n"
            )
        domains_init_body += f"""
            self.{domain_name} = {domain_name_in_title_case}Domain(hapt)"""

    # TODO reverse order
    out = f"""
    # This file is generated automatically by homeassistant_python_typer

    # pyright: reportUnusedImport = false
    from appdaemon.adbase import ADBase
    import homeassistant_python_typer_helpers as hapth
    from typing import TypeAlias, Literal, Tuple, Any


    # Declare type aliases for all "select" options
{retab(enum_declarations_body)}


    # Declare all services classes
{retab(services_classes_body)}


    # Declare entities
{retab(entities_classes_body)}


    # Declare domains
{retab(domains_classes_body)}


    # Finally register all domains in a final Entities object
    class Entities:
        def __init__(self, ad: ADBase):
            hapt = hapth.HaptSharedState(ad)
{domains_init_body}
    """

    out = remove_common_indent_levels(out).strip("\n")
    if not out.endswith("\n"):
        out += "\n"

    with open(output_filename, "w") as output_file:
        output_file.write(out)


class HomeAssistantClient:
    def __init__(self, url: str, token: str):
        if url.endswith("/"):
            url = url[:-1]
        if not url.endswith("/api"):
            url = f"{url}/api"
        self.url = url
        self.token = token

    def get(self, path: str):
        return requests.get(
            f"{self.url}/{path}", headers={"Authorization": f"Bearer {self.token}"}
        ).json()


def remove_common_indent_levels(text: str) -> str:
    if text.strip() == "":
        return ""
    lines = text.split("\n")
    common_indent = min(
        len(line) - len(line.lstrip()) for line in lines if line.strip() != ""
    )
    return "\n".join(line[common_indent:].rstrip() for line in lines)


def tab(text: str, n: int = 1) -> str:
    return "\n".join((f"{"    "*n}{line}" for line in text.split("\n")))


def retab(text: str, n: int = 1) -> str:
    return tab(remove_common_indent_levels(text), n)


if __name__ == "__main__":
    main()
