from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    Optional,
    ParamSpec,
    TypeAlias,
)
from appdaemon.adbase import ADBase
from appdaemon.utils import sync_wrapper

OnOff: TypeAlias = Literal["on", "off"]

FunctionArgsGeneric = ParamSpec("FunctionArgsGeneric")


class HaptSharedState:
    """
    Shared state for Home Assistant Python Typer entities.

    Methods:
        __init__(ad: ADBase): Initializes the shared state with the given AppDaemon base instance.
    """

    state_cache: dict[str, Any]
    full_cache: dict[str, Any]

    def __init__(self, ad: ADBase):
        self.ad = ad
        self.adapi = ad.get_ad_api()
        self.state_cache = {}
        self.full_cache = {}

    def clear_caches(self):
        """
        Clear repeatable read caches. This is called by event handlers, at the beginning of each event handling,
        since time has passed so the state of entities may have changed.
        """
        self.state_cache.clear()
        self.full_cache.clear()


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

        # Unfortunately we need those for the sync_wrapper to work
        self.name = self.hapt.ad.name
        "Name of the appdaemon app that this Entity is linked to - not a property of the entity itself"
        self.AD = self.hapt.ad.AD
        "AppDaemon instance"

    @sync_wrapper
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
        return await self.AD.services.call_service(
            self.namespace, domain, service, data
        )

    # We will eventually try typing this as well but there's no API to know for sure what can be in there this time
    # so for now we'll skip it
    @sync_wrapper
    async def query_state(
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

    def get_state_repeatable_read(
        self,
        attribute: str | None = None,
        default: Any = None,
    ) -> Any:
        """
        Get state of the entity, or any of its attributes, or all its attributes.

        This method has repeatable read semantics, that is, it will return the same value if called multiple times
        in the same event handling. This generally naturally avoiding race conditions when writing if/else logic based
        on the states.

        Returns default if the attribute is not found.

        Args:
            attribute (str): The attribute to get. If None, the state of the entity is returned. If 'attributes',
            the dictionary of attributes, if the name of an attribute, the value of that attribute.
            default (Any): The value to return if the attribute is not found (or the entity is not found).
        """

        if attribute is None:
            if self.entity_id in self.hapt.state_cache:
                return self.hapt.state_cache[self.entity_id]
            else:
                entity_state = self.query_state(attribute=None, copy=True)
                self.hapt.state_cache[self.entity_id] = entity_state
                return entity_state
        else:
            entity_state: dict[str, Any]
            if self.entity_id in self.hapt.full_cache:
                entity_state = self.hapt.full_cache[self.entity_id]
            else:
                entity_state = self.query_state(attribute="all", copy=True)
                self.hapt.full_cache[self.entity_id] = entity_state
                self.hapt.state_cache[self.entity_id] = entity_state["state"]

            # From there, same logic as AppDaemon's own get_state
            if attribute == "all":
                return entity_state
            if attribute in entity_state["attributes"]:
                return entity_state["attributes"][attribute]
            if attribute in entity_state:
                return entity_state[attribute]
            return default

    def listen_state(
        self,
        callback: Callable[FunctionArgsGeneric, None],
        attribute: str | None = None,
        *args: FunctionArgsGeneric.args,
        **kwargs: FunctionArgsGeneric.kwargs,
    ) -> None:
        """
        Listen to state changes of the entity.

        Args:
            callback (Callable): The callback to call when the state changes.
            attribute (str): The attribute to listen to. If None, the state of the entity is listened to.
            *args: Additional arguments to pass to the callback.
            **kwargs: Additional keyword arguments to pass to the callback.
        """

        def callback_wrapper(
            entity: str,
            attribute: str | None,
            old: Any,
            new: Any,
            cb_args: dict[str, object],
        ):
            self.hapt.clear_caches()
            assert self.entity_id == entity
            if attribute is None:
                self.hapt.state_cache[self.entity_id] = new
            elif attribute == "all":
                self.hapt.full_cache[self.entity_id] = new
                self.hapt.state_cache[self.entity_id] = new["state"]
            callback(*args, **kwargs)

        self.hapt.adapi.listen_state(callback_wrapper, self.entity_id)


class Domain:
    def __init__(self, hapt: HaptSharedState, domain_name: str):
        self._hapt = hapt
        self._domain_name = domain_name

    if not TYPE_CHECKING:

        def __getattr__(self, entity_name: str) -> object:
            # We lazily initialize fields as they get used, so that initializing `Entities`
            # doesn't allocate unnecessary resources: each app is probably going to sparsely use
            # the entities.
            # We only enter __getattr__ if the attribute is not already set.
            if entity_class := self.__class__.__annotations__.get(entity_name):
                entity = entity_class(
                    hapt=self._hapt, entity_id=f"{self._domain_name}.{entity_name}"
                )
                setattr(self, entity_name, entity)  # cache it for next time
                return entity
            raise AttributeError(
                f"Entity {entity_name} not found in domain {self._domain_name}"
            )


def rgb_color(
    rgb_array_or_str: list[int] | tuple[int, int, int] | str
) -> tuple[int, int, int]:
    if isinstance(rgb_array_or_str, str):
        # Convert from hashtag hex representation to the RGB tuple
        if rgb_array_or_str.startswith("#"):
            rgb_array_or_str = rgb_array_or_str[1:]
        if len(rgb_array_or_str) != 6:
            raise ValueError("RGB color string must have 6 characters (or 7 with #)")
        rgb_array_or_str = [int(rgb_array_or_str[i : i + 2], 16) for i in (0, 2, 4)]
    if isinstance(rgb_array_or_str, list):
        if len(rgb_array_or_str) != 3:
            raise ValueError("RGB color array must have 3 elements (red, green, blue)")
        red, green, blue = rgb_array_or_str
        if not all(0 <= color <= 255 for color in rgb_array_or_str):
            raise ValueError("RGB color values must be between 0 and 255")
        return red, green, blue
    return rgb_array_or_str


class OnOffState(Entity):
    """
    Represents any entity whose state can only be "on" or "off".

    This provides better typing and an `is_on` function for entities that can only be on or off.
    """

    def state(
        self,
    ) -> OnOff:
        """
        Retrieve the state of the entity.

        Returns:
            "on"/"off": The state of the entity.
        """
        return super().get_state_repeatable_read()

    def is_on(self) -> bool:
        """
        Check if the entity is on.

        Returns:
            bool: True if the entity is on, False otherwise.
        """
        entity_state = self.state()
        match entity_state:
            case "off":
                return False
            case "on":
                return True
            case _:  # pyright: ignore[reportUnnecessaryComparison]
                raise ValueError(f"Unexpected entity state: {entity_state}")

    def is_off(self) -> bool:
        """
        Check if the entity is off.

        Returns:
            bool: True if the entity is off, False otherwise.
        """
        return not self.is_on()


class Light(OnOffState):
    """
    Represents a Light entity in Home Assistant.

    Any entity in the `light` domain when introspected will inherit this class
    """


class BinarySensor(OnOffState):
    """
    Represents a Binary Sensor entity in Home Assistant.

    Any entity in the `binary_sensor` domain when introspected will inherit this class
    """
