from datetime import datetime
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
            if default is not None:
                return default
            raise ValueError(
                f"Attribute {attribute} not found for entity {self.entity_id}"
            )

    def listen_state(
        self,
        callback: Callable[FunctionArgsGeneric, Any],
        attribute: str | None = None,
        new: Any = None,
        old: Any = None,
        duration_s: int | None = None,
        timeout_s: int | None = None,
        *args: FunctionArgsGeneric.args,
        **kwargs: FunctionArgsGeneric.kwargs,
    ) -> None:
        """
        Listen to state changes of the entity.

        Args:
            callback (Callable): The callback to call when the state changes.
            attribute (str): The attribute to listen to. If None, the state of the entity is listened to.

            new (optional): If ``new`` is supplied as a parameter, callbacks will only be made if the
                state of the selected attribute (usually state) in the new state match the value
                of ``new``. The parameter type is defined by the namespace or plugin that is responsible
                for the entity. If it looks like a float, list, or dictionary, it may actually be a string.
                If ``new`` is a callable (lambda, function, etc), then it will be invoked with the new state,
                and if it returns ``True``, it will be considered to match.
            old (optional): If ``old`` is supplied as a parameter, callbacks will only be made if the
                state of the selected attribute (usually state) in the old state match the value
                of ``old``. The same caveats on types for the ``new`` parameter apply to this parameter.
                If ``old`` is a callable (lambda, function, etc), then it will be invoked with the old state,
                and if it returns a ``True``, it will be considered to match.

            duration_s (int, optional): If ``duration`` is supplied as a parameter, the callback will not
                fire unless the state listened for is maintained for that number of seconds. This
                requires that a specific attribute is specified (or the default of ``state`` is used),
                and should be used in conjunction with the ``old`` or ``new`` parameters, or both. When
                the callback is called, it is supplied with the values of ``entity``, ``attr``, ``old``,
                and ``new`` that were current at the time the actual event occurred, since the assumption
                is that none of them have changed in the intervening period.

                If you use ``duration`` when listening for an entire device type rather than a specific
                entity, or for all state changes, you may get unpredictable results, so it is recommended
                that this parameter is only used in conjunction with the state of specific entities.

            timeout_s (int, optional): If ``timeout`` is supplied as a parameter, the callback will be created as normal,
                 but after ``timeout`` seconds, the callback will be removed. If activity for the listened state has
                 occurred that would trigger a duration timer, the duration timer will still be fired even though the
                 callback has been deleted.
            *args: Additional arguments to pass to the callback.
            **kwargs: Additional keyword arguments to pass to the callback.
        """

        def callback_wrapper(
            entity: str,
            attribute: str | None,
            old: Any,
            new: Any,
            cb_args: dict[str, object],
        ) -> None:
            self.hapt.clear_caches()
            assert self.entity_id == entity
            if attribute is None:
                self.hapt.state_cache[self.entity_id] = new
            elif attribute == "all":
                self.hapt.full_cache[self.entity_id] = new
                self.hapt.state_cache[self.entity_id] = new["state"]
            callback(*args, **kwargs)

        listen_kwargs: dict[str, Any] = {}
        for kwarg_name, kwarg_value in {
            "new": new,
            "old": old,
            "duration": duration_s,
            "timeout": timeout_s,
        }.items():
            if kwarg_value is not None:
                listen_kwargs[kwarg_name] = kwarg_value
        if "duration" in listen_kwargs:
            # I don't think there's a use-case for anything else...
            listen_kwargs["immediate"] = True

        self.hapt.adapi.listen_state(callback_wrapper, self.entity_id, **listen_kwargs)

    def last_changed(self) -> datetime:
        """
        Get the last time the entity changed state.

        Returns:
            datetime: The last time the entity changed state.
        """
        return datetime.fromisoformat(
            self.get_state_repeatable_read(attribute="last_changed")
        )


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


class InputButton(Entity):
    """
    Represents an Input Button entity in Home Assistant.

    Any entity in the `input_button` domain when introspected will inherit this class
    """

    def last_pressed_at(self) -> datetime | None:
        """
        Retrieve when the button was last pressed.

        Returns:
            datetime | None: When the button was last pressed, or None if we don't know of a press.
        """
        state = self.get_state_repeatable_read()
        if state == "unknown":
            return None
        return datetime.fromisoformat(state)


class Climate(Entity):
    """
    Represents a Climate (Thermostat) entity in Home Assistant.

    Any entity in the `climate` domain when introspected will inherit this class if it also has
    the `temperature` and `current_temperature` attributes.
    """

    def temperature(self) -> float:
        """
        Retrieve the target temperature of the thermostat.

        Returns:
            float: The target temperature of the thermostat.
        """
        return self.get_state_repeatable_read(attribute="temperature")

    def current_temperature(self) -> float:
        """
        Retrieve the current temperature of the thermostat (sensor).

        Returns:
            float: The current temperature of the thermostat.
        """
        return self.get_state_repeatable_read(attribute="current_temperature")
