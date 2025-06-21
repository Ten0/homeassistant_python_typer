import requests
import json
import os
import sys

from .infer_entities import infer_entities
from .infer_headless_services import infer_headless_services
from .dataclasses import *
from .builder import HaptBuilder
from .helpers import *


def main():
    # Read from env variables
    is_running_in_addon = "SUPERVISOR_TOKEN" in os.environ
    if is_running_in_addon:
        ha_url = os.environ.get("HOMEASSISTANT_URL", "http://supervisor/core")
        ha_token = os.environ.get("HOMEASSISTANT_TOKEN", os.environ["SUPERVISOR_TOKEN"])
    else:
        ok = True
        if "HOMEASSISTANT_URL" not in os.environ:
            print("Please set the HOMEASSISTANT_URL environment variable")
            print("For instance: export HOMEASSISTANT_URL=http://192.168.1.48:8123")
            ok = False
        if "HOMEASSISTANT_TOKEN" not in os.environ:
            print("Please set the HOMEASSISTANT_TOKEN environment variable")
            print("For instance: export HOMEASSISTANT_TOKEN=<your_long_lived_token>")
            print(
                "Documentation on how to get a token: https://community.home-assistant.io/t/how-to-get-long-lived-access-token/162159/5"
            )
            ok = False
        if not ok:
            sys.exit(1)
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

    builder = HaptBuilder()

    infer_entities(
        builder=builder,
        hm_entities=hm_entities,
        hm_services=hm_services,
    )
    infer_headless_services(builder, hm_services)

    services_classes = [
        service_class for _, service_class in builder.classes_per_body.items()
    ]
    services_classes.sort(key=lambda s: s.name)  # sort by name for consistency
    builder.entities.sort(key=lambda e: e.name)  # sort by name for consistency
    domains_classes = [
        (domain_name, domain_entities)
        for domain_name, domain_entities in builder.domains.items()
    ]
    domains_classes.sort(key=lambda x: x[0])  # sort by name for consistency
    for _, domain in domains_classes:
        domain.entities.sort(key=lambda e: e.name)

    enum_declarations_body = "\n".join(
        (type_alias.declaration for type_alias in builder.enum_types.values())
    )
    services_classes_body = "\n\n".join(
        (service_class.body for service_class in services_classes)
    ).lstrip("\n")
    entities_classes_body = "\n\n".join(
        (entity.declaration_body for entity in builder.entities)
    )
    domains_classes_body = ""
    domains_init_body = ""
    for domain_name, domain in domains_classes:
        domain_name_in_title_case = domain_name.title()
        if domains_classes_body != "":
            domains_classes_body += "\n"
        domains_classes_body += f"""
        class {domain_name_in_title_case}Domain(hapth.Domain):
            def __init__(self, hapt: hapth.HaptSharedState):
                super().__init__(hapt, "{domain_name}")\n\n""".lstrip(
            "\n"
        )
        for entity in domain.entities:
            entity_docstring = (
                ("\n" + repr(entity.friendly_name)) if entity.friendly_name else ""
            )
            domains_classes_body += (
                tab(
                    f"{entity.name}: {entity.type_name}{entity_docstring}",
                    3,
                )
                + "\n\n"
            )
        for service in domain.services:
            line_break = "\n"  # python 3.11 support
            domains_classes_body += (
                f"""{retab(service.declaration.lstrip(line_break), 3)}\n\n"""
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


    # Finally register all domains in a final HomeAssistant object
    class HomeAssistant:
        def __init__(self, ad: ADBase):
            hapt = hapth.HaptSharedState(ad)
            self.hapt = hapt # So that users can call clear_caches() if writing appdaemon handlers directly
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


if __name__ == "__main__":
    main()
