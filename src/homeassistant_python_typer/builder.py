from .dataclasses import *
from typing import Any, Iterable, Tuple


class HaptBuilder:
    classes_per_body: dict[str, EntitySuperclass] = {}
    "Key is body of the class, for find-or-create"

    entities: list[Entity] = []
    "All the entities (types) that we'll need to declare"

    domains: dict[str, Domain] = {}
    "domain name -> All domains, with their entities, for declaration"

    enum_types: dict[Tuple[str, str], TypeAlias] = {}
    "(field name, type) -> (type alias name, type alias declaration)"

    imports: set[str] = set()

    def enum_type(
        self,
        field_name: str,
        type_name_prefix: str,
        options: Iterable[str | dict[str, Any]],
    ):
        "Finds or create the necessary enum in enum_types, and returns its name"
        options_repr: Iterable[str] = (
            repr(option["value"]) if isinstance(option, dict) else repr(option)
            for option in options
        )
        type = f"Literal[{', '.join(options_repr)}]"
        if (field_name, type) in self.enum_types:
            return self.enum_types[(field_name, type)].name
        else:
            enum_type_name = f"{type_name_prefix}{len(self.enum_types)}"
            self.enum_types[(field_name, type)] = TypeAlias(
                name=enum_type_name,
                declaration=f"{enum_type_name}: TypeAlias = {type}",
            )
            return enum_type_name
