from dataclasses import dataclass
from typing import Any, Iterable, Tuple


@dataclass
class ServiceClass:
    name: str
    body: str


@dataclass
class Entity:
    name: str
    declaration_body: str


@dataclass
class DomainEntity:
    name: str
    type_name: str
    friendly_name: str | None


@dataclass
class Domain:
    entities: list[DomainEntity]


@dataclass
class TypeAlias:
    name: str
    declaration: str


def enum_type(
    field_name: str,
    type_name_prefix: str,
    options: Iterable[str | dict[str, Any]],
    enum_types: dict[Tuple[str, str], TypeAlias],
):
    "Finds or create the necessary enum in enum_types, and returns its name"
    options_repr: Iterable[str] = (
        repr(option["value"]) if isinstance(option, dict) else repr(option)
        for option in options
    )
    type = f"Literal[{", ".join(options_repr)}]"
    if (field_name, type) in enum_types:
        return enum_types[(field_name, type)].name
    else:
        enum_type_name = f"{type_name_prefix}{len(enum_types)}"
        enum_types[(field_name, type)] = TypeAlias(
            name=enum_type_name,
            declaration=f"{enum_type_name}: TypeAlias = {type}",
        )
        return enum_type_name
