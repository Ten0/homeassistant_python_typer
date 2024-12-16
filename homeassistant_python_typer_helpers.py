from typing import Any, Literal, Optional, TypeAlias
from appdaemon.adbase import ADBase

OnOff: TypeAlias = Literal["on", "off"]


class HaptSharedState:
    """
    Shared state for Home Assistant Python Typer entities.

    Methods:
        __init__(ad: ADBase): Initializes the shared state with the given AppDaemon base instance.
    """

    def __init__(self, ad: ADBase):
        self.ad = ad
        self.adapi = ad.get_ad_api()


class Entity:
    """
    Represents a generic entity in Home Assistant.

    This is the base class for all introspected entities, however each entity will have its own class with all the
    methods that are available for it.
    """

    def __init__(
        self, hapt: HaptSharedState, entity_id: str, namespace: str | None = None
    ):
        self.hapt = hapt
        self.entity_id = entity_id
        self.namespace = namespace or self.hapt.ad.namespace

    async def call(self, domain: str, service: str, data: dict[str, Any]) -> None:
        """
        Asynchronously calls a Home Assistant service.
        This is a largely internal method and should typically not be called directly by users: it bypasses typing.

        Args:
            domain (str): The domain of the service to call (e.g., 'light', 'switch').
            service (str): The name of the service to call (e.g., 'turn_on', 'turn_off').
            data (dict[str, Any]): A dictionary containing the service data. The 'entity_id' key will be set to the
            entity ID of this instance, and other parameters will be passed as-is to the HomeAssistant API.

        Returns:
            None
        """
        # Remove any None values from the data: AFAIK HomeAssistant doesn't need actually specified but None values
        # If that were the case we'd need a different placeholder types for None compared to unspecified.
        data = {k: v for k, v in data.items() if v is not None}

        # Add entity id to the call (this is always the convention in HomeAssistant's API)
        data["entity_id"] = self.entity_id

        # make it so that potential error messages would tell which app the call is from
        # (this is used directly by call_service)
        data["__name"] = self.hapt.ad.name

        # TODO check returns and headless async calls in async doc
        return await self.hapt.ad.AD.services.call_service(
            self.namespace, domain, service, data
        )

    # We will eventually try typing this as well but there's no API to know for sure what can be in there this time
    # so for now we'll skip it
    async def get_state_raw(
        self,
        attribute: str | None = None,
        default: Any = None,
        copy: bool = True,
        **kwargs: Optional[Any],
    ) -> Any:
        """
        Get state of the entity, or any of its attributes, or all its attributes

        Args:
            attribute (str): The attribute to get. If None, the state of the entity is returned. If 'attributes',
            the dictionary of attributes (copied unless specified otherwise), if the name of an attribute,
            the value of that attribute.
            default (Any): The value to return if the attribute is not found (or the entity is not found).
            copy (bool): Whether to return a copy of the state or the original object.
            **kwargs: Additional keyword arguments to pass to the API call.
        """
        return await self.hapt.adapi.get_entity(
            self.entity_id, namespace=self.namespace
        ).get_state(attribute=attribute, default=default, copy=copy, **kwargs)


class Light(Entity):
    """
    Represents a Light entity in Home Assistant.

    Any entity in the `light` domain when introspected will inherit this class
    """

    async def state(
        self,
    ) -> OnOff:
        """
        Retrieve the state of the light.

        Returns:
            "on"/"off": The state of the entity.
        """
        return await super().get_state_raw()

    async def is_on(self) -> bool:
        """
        Check if the light is on.

        Returns:
            bool: True if the light is on, False otherwise.
        """
        light_state = await self.state()
        match light_state:
            case "off":
                return False
            case "on":
                return True
            case _:  # type: ignore[reportUnnecessaryComparison]
                raise ValueError(f"Unexpected light state: {light_state}")
