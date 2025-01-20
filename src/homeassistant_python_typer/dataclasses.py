from dataclasses import dataclass
from typing import Any


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
class ServiceEndpoint:
    declaration: str


@dataclass
class Domain:
    services: list[ServiceEndpoint]
    entities: list[DomainEntity]


@dataclass
class TypeAlias:
    name: str
    declaration: str


@dataclass
class EntityService:
    domain: str
    name: str
    data: Any
