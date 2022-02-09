import sys
from asyncio import ensure_future, get_event_loop, iscoroutinefunction
from functools import wraps
from importlib import import_module
from importlib.util import resolve_name
from inspect import getmembers
from logging import Logger
from types import ModuleType
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from .api.cache import Cache
from .api.cache import Item as Build
from .api.error import InteractionException, JSONException
from .api.gateway import WebSocket
from .api.http import HTTPClient
from .api.models.flags import Intents
from .api.models.guild import Guild
from .api.models.misc import MISSING, Snowflake
from .api.models.team import Application
from .base import get_logger
from .decor import command
from .decor import component as _component
from .enums import ApplicationCommandType
from .models.command import ApplicationCommand, Option
from .models.component import Button, Modal, SelectMenu

log: Logger = get_logger("client")
_token: str = ""  # noqa
_cache: Optional[Cache] = None


class Client:
    """
    A class representing the client connection to Discord's gateway and API via. WebSocket and HTTP.

    :ivar AbstractEventLoop _loop: The asynchronous event loop of the client.
    :ivar HTTPClient _http: The user-facing HTTP connection to the Web API, as its own separate client.
    :ivar WebSocket _websocket: An object-orientation of a websocket server connection to the Gateway.
    :ivar Intents _intents: The Gateway intents of the application. Defaults to ``Intents.DEFAULT``.
    :ivar Optional[List[Tuple[int]]] _shard: The list of bucketed shards for the application's connection.
    :ivar Optional[Presence] _presence: The RPC-like presence shown on an application once connected.
    :ivar str _token: The token of the application used for authentication when connecting.
    :ivar Optional[Dict[str, ModuleType]] _extensions: The "extensions" or cog equivalence registered to the main client.
    :ivar Application me: The application representation of the client.
    """

    def __init__(
        self,
        token: str,
        **kwargs,
    ) -> None:
        r"""
        Establishes a client connection to the Web API and Gateway.

        :param token: The token of the application for authentication and connection.
        :type token: str
        :param \**kwargs: Multiple key-word arguments able to be passed through.
        :type \**kwargs: dict
        """

        # Arguments
        # ~~~~~~~~~
        # token : str
        #     The token of the application for authentication and connection.
        # intents? : Optional[Intents]
        #     Allows specific control of permissions the application has when connected.
        #     In order to use multiple intents, the | operator is recommended.
        #     Defaults to ``Intents.DEFAULT``.
        # shards? : Optional[List[Tuple[int]]]
        #     Dictates and controls the shards that the application connects under.
        # presence? : Optional[Presence]
        #     Sets an RPC-like presence on the application when connected to the Gateway.
        # disable_sync? : Optional[bool]
        #     Controls whether synchronization in the user-facing API should be automatic or not.

        self._loop = get_event_loop()
        self._http = HTTPClient(token=token)
        self._intents = kwargs.get("intents", Intents.DEFAULT)
        self._websocket = WebSocket(intents=self._intents)
        self._shard = kwargs.get("shards", [])
        self._presence = kwargs.get("presence")
        self._token = token
        self._extensions = {}
        self.me = None
        _token = self._token  # noqa: F841
        _cache = self._http.cache  # noqa: F841

        if kwargs.get("disable_sync"):
            self._automate_sync = False
            log.warning(
                "Automatic synchronization has been disabled. Interactions may need to be manually synchronized."
            )
        else:
            self._automate_sync = True

        data = self._loop.run_until_complete(self._http.get_current_bot_information())
        self.me = Application(**data)

    def start(self) -> None:
        """Starts the client session."""
        self._loop.run_until_complete(self._ready())

    def __register_events(self) -> None:
        """Registers all raw gateway events to the known events."""
        self._websocket.dispatch.register(self.__raw_socket_create)
        self._websocket.dispatch.register(self.__raw_channel_create, "on_channel_create")
        self._websocket.dispatch.register(self.__raw_message_create, "on_message_create")
        self._websocket.dispatch.register(self.__raw_guild_create, "on_guild_create")

    async def __compare_sync(self, data: dict, pool: List[dict]) -> bool:
        """
        Compares an application command during the synchronization process.

        :param data: The application command to compare.
        :type data: dict
        :param pool: The "pool" or list of commands to compare from.
        :type pool: List[dict]
        :return: Whether the command has changed or not.
        :rtype: bool
        """
        attrs: List[str] = ["type", "name", "description", "options", "guild_id"]
        log.info(f"Current attributes to compare: {', '.join(attrs)}.")
        clean: bool = True

        for command in pool:
            if command["name"] == data["name"]:
                for attr in attrs:
                    if hasattr(data, attr) and command.get(attr) == data.get(attr):
                        continue
                    else:
                        clean = False

        return clean

    async def __create_sync(self, data: dict) -> None:
        """
        Creates an application command during the synchronization process.

        :param data: The application command to create.
        :type data: dict
        """
        log.info(f"Creating command {data['name']}.")

        command: ApplicationCommand = ApplicationCommand(
            **(
                await self._http.create_application_command(
                    application_id=self.me.id, data=data, guild_id=data.get("guild_id")
                )
            )
        )
        self._http.cache.interactions.add(Build(id=command.name, value=command))

    async def __bulk_update_sync(self, data: List[dict], delete: Optional[bool] = False) -> None:
        """
        Bulk updates a list of application commands during the synchronization process.

        The theory behind this is that instead of sending individual ``PATCH``
        requests to the Web API, we collect the commands needed and do a bulk
        overwrite instead. This is to mitigate the amount of calls, and hopefully,
        chances of hitting rate limits during the readying state.

        :param data: The application commands to update.
        :type data: List[dict]
        :param delete?: Whether these commands are being deleted or not.
        :type delete: Optional[bool]
        """
        guild_commands: dict = {}
        global_commands: List[dict] = []

        for command in data:
            if command.get("guild_id"):
                if guild_commands.get(command["guild_id"]):
                    guild_commands[command["guild_id"]].append(command)
                else:
                    guild_commands[command["guild_id"]] = [command]
            else:
                global_commands.append(command)

            self._http.cache.interactions.add(
                Build(id=command["name"], value=ApplicationCommand(**command))
            )

        for guild, commands in guild_commands.items():
            log.info(
                f"Guild commands {', '.join(command['name'] for command in commands)} under ID {guild} have been {'deleted' if delete else 'synced'}."
            )
            await self._http.overwrite_application_command(
                application_id=self.me.id,
                data=[] if delete else commands,
                guild_id=guild,
            )

        if global_commands:
            log.info(
                f"Global commands {', '.join(command['name'] for command in global_commands)} have been {'deleted' if delete else 'synced'}."
            )
            await self._http.overwrite_application_command(
                application_id=self.me.id, data=[] if delete else global_commands
            )

    async def _synchronize(self, payload: Optional[dict] = None) -> None:
        """
        Synchronizes a command from the client-facing API to the Web API.

        :ivar payload?: The application command to synchronize. Defaults to ``None`` where a global synchronization process begins.
        :type payload: Optional[dict]
        """
        cache: Optional[List[dict]] = self._http.cache.interactions.view

        if cache:
            log.info("A command cache was detected, using for synchronization instead.")
            commands: List[dict] = cache
        else:
            log.info("No command cache was found present, retrieving from Web API instead.")
            commands: Optional[Union[dict, List[dict]]] = await self._http.get_application_commands(
                application_id=self.me.id, guild_id=payload.get("guild_id") if payload else None
            )

        # TODO: redo error handling.
        if isinstance(commands, dict):
            if commands.get("code"):  # Error exists.
                raise JSONException(commands["code"], message=commands["message"] + " |")
                # TODO: redo error handling.
        elif isinstance(commands, list):
            for command in commands:
                if command.get("code"):
                    # Error exists.
                    raise JSONException(command["code"], message=command["message"] + " |")

        names: List[str] = (
            [command["name"] for command in commands if command.get("name")] if commands else []
        )
        to_sync: list = []
        to_delete: list = []

        if payload:
            log.info(f"Checking command {payload['name']}.")
            if payload["name"] in names:
                if not await self.__compare_sync(payload, commands):
                    to_sync.append(payload)
            else:
                await self.__create_sync(payload)
        else:
            for command in commands:
                if command not in cache:
                    to_delete.append(command)

        await self.__bulk_update_sync(to_sync)
        await self.__bulk_update_sync(to_delete, delete=True)

    async def _ready(self) -> None:
        """
        Prepares the client with an internal "ready" check to ensure
        that all conditions have been met in a chronological order:

        .. code-block::

            CLIENT START
            |___ GATEWAY
            |   |___ READY
            |   |___ DISPATCH
            |___ SYNCHRONIZE
            |   |___ CACHE
            |___ DETECT DECORATOR
            |   |___ BUILD MODEL
            |   |___ SYNCHRONIZE
            |   |___ CALLBACK
            LOOP
        """
        ready: bool = False

        try:
            if self.me.flags is not None:
                # This can be None.
                if self._intents.GUILD_PRESENCES in self._intents and not (
                    self.me.flags.GATEWAY_PRESENCE in self.me.flags
                    or self.me.flags.GATEWAY_PRESENCE_LIMITED in self.me.flags
                ):
                    raise RuntimeError("Client not authorised for the GUILD_PRESENCES intent.")
                if self._intents.GUILD_MEMBERS in self._intents and not (
                    self.me.flags.GATEWAY_GUILD_MEMBERS in self.me.flags
                    or self.me.flags.GATEWAY_GUILD_MEMBERS_LIMITED in self.me.flags
                ):
                    raise RuntimeError("Client not authorised for the GUILD_MEMBERS intent.")
                if self._intents.GUILD_MESSAGES in self._intents and not (
                    self.me.flags.GATEWAY_MESSAGE_CONTENT in self.me.flags
                    or self.me.flags.GATEWAY_MESSAGE_CONTENT_LIMITED in self.me.flags
                ):
                    log.critical("Client not authorised for the MESSAGE_CONTENT intent.")
            else:
                # This is when a bot has no intents period.
                if self._intents.value != Intents.DEFAULT.value:
                    raise RuntimeError("Client not authorised for any privileged intents.")

            self.__register_events()
            if self._automate_sync:
                await self._synchronize()
            ready = True
        except Exception as error:
            log.critical(f"Could not prepare the client: {error}")
        finally:
            if ready:
                log.debug("Client is now ready.")
                await self._login()

    async def _login(self) -> None:
        """Makes a login with the Discord API."""
        while not self._websocket.closed:
            await self._websocket.connect(self._token, self._shard, self._presence)

    def event(self, coro: Coroutine, name: Optional[str] = MISSING) -> Callable[..., Any]:
        """
        A decorator for listening to events dispatched from the
        Gateway.

        :param coro: The coroutine of the event.
        :type coro: Coroutine
        :param name(?): The name of the event. If not given, this defaults to the coroutine's name.
        :type name: Optional[str]
        :return: A callable response.
        :rtype: Callable[..., Any]
        """
        self._websocket.dispatch.register(coro, name if name is not MISSING else coro.__name__)
        return coro

    def command(
        self,
        *,
        type: Optional[Union[int, ApplicationCommandType]] = ApplicationCommandType.CHAT_INPUT,
        name: Optional[str] = MISSING,
        description: Optional[str] = MISSING,
        scope: Optional[Union[int, Guild, List[int], List[Guild]]] = MISSING,
        options: Optional[
            Union[Dict[str, Any], List[Dict[str, Any]], Option, List[Option]]
        ] = MISSING,
        default_permission: Optional[bool] = MISSING,
    ) -> Callable[..., Any]:
        """
        A decorator for registering an application command to the Discord API,
        as well as being able to listen for ``INTERACTION_CREATE`` dispatched
        gateway events.

        The structure of a chat-input command:

        .. code-block:: python

            @command(name="command-name", description="this is a command.")
            async def command_name(ctx):
                ...

        You are also able to establish it as a message or user command by simply passing
        the ``type`` kwarg field into the decorator:

        .. code-block:: python

            @command(type=interactions.ApplicationCommandType.MESSAGE, name="Message Command")
            async def message_command(ctx):
                ...

        The ``scope`` kwarg field may also be used to designate the command in question
        applicable to a guild or set of guilds.

        :param type?: The type of application command. Defaults to :meth:`interactions.enums.ApplicationCommandType.CHAT_INPUT` or ``1``.
        :type type: Optional[Union[str, int, ApplicationCommandType]]
        :param name: The name of the application command. This *is* required but kept optional to follow kwarg rules.
        :type name: Optional[str]
        :param description?: The description of the application command. This should be left blank if you are not using ``CHAT_INPUT``.
        :type description: Optional[str]
        :param scope?: The "scope"/applicable guilds the application command applies to.
        :type scope: Optional[Union[int, Guild, List[int], List[Guild]]]
        :param options?: The "arguments"/options of an application command. This should be left blank if you are not using ``CHAT_INPUT``.
        :type options: Optional[Union[Dict[str, Any], List[Dict[str, Any]], Option, List[Option]]]
        :param default_permission?: The default permission of accessibility for the application command. Defaults to ``True``.
        :type default_permission: Optional[bool]
        :return: A callable response.
        :rtype: Callable[..., Any]
        """

        def decorator(coro: Coroutine) -> Callable[..., Any]:
            if name is MISSING:
                raise InteractionException(11, message="Your command must have a name.")

            if type == ApplicationCommandType.CHAT_INPUT and description is MISSING:
                raise InteractionException(
                    11, message="Chat-input commands must have a description."
                )

            if not len(coro.__code__.co_varnames):
                raise InteractionException(
                    11, message="Your command needs at least one argument to return context."
                )
            if options is not MISSING and len(coro.__code__.co_varnames) + 1 < len(options):
                raise InteractionException(
                    11,
                    message="You must have the same amount of arguments as the options of the command.",
                )

            commands: List[ApplicationCommand] = command(
                type=type,
                name=name,
                description=description,
                scope=scope,
                options=options,
                default_permission=default_permission,
            )

            if self._automate_sync:
                if self._loop.is_running():
                    [self._loop.create_task(self._synchronize(command)) for command in commands]
                else:
                    [
                        self._loop.run_until_complete(self._synchronize(command))
                        for command in commands
                    ]

            return self.event(coro, name=f"command_{name}")

        return decorator

    def message_command(
        self,
        *,
        name: str,
        scope: Optional[Union[int, Guild, List[int], List[Guild]]] = MISSING,
        default_permission: Optional[bool] = MISSING,
    ) -> Callable[..., Any]:
        """
        A decorator for registering a message context menu to the Discord API,
        as well as being able to listen for ``INTERACTION_CREATE`` dispatched
        gateway events.

        The structure of a message context menu:

        .. code-block:: python

            @message_command(name="Context menu name")
            async def context_menu_name(ctx):
                ...

        The ``scope`` kwarg field may also be used to designate the command in question
        applicable to a guild or set of guilds.

        :param name: The name of the application command.
        :type name: Optional[str]
        :param scope?: The "scope"/applicable guilds the application command applies to. Defaults to ``None``.
        :type scope: Optional[Union[int, Guild, List[int], List[Guild]]]
        :param default_permission?: The default permission of accessibility for the application command. Defaults to ``True``.
        :type default_permission: Optional[bool]
        :return: A callable response.
        :rtype: Callable[..., Any]
        """

        def decorator(coro: Coroutine) -> Callable[..., Any]:
            if not len(coro.__code__.co_varnames):
                raise InteractionException(
                    11,
                    message="Your command needs at least one argument to return context.",
                )

            commands: List[ApplicationCommand] = command(
                type=ApplicationCommandType.MESSAGE,
                name=name,
                scope=scope,
                default_permission=default_permission,
            )

            if self._automate_sync:
                if self._loop.is_running():
                    [self._loop.create_task(self._synchronize(command)) for command in commands]
                else:
                    [
                        self._loop.run_until_complete(self._synchronize(command))
                        for command in commands
                    ]

            return self.event(coro, name=f"command_{name}")

        return decorator

    def user_command(
        self,
        *,
        name: str,
        scope: Optional[Union[int, Guild, List[int], List[Guild]]] = MISSING,
        default_permission: Optional[bool] = MISSING,
    ) -> Callable[..., Any]:
        """
        A decorator for registering a user context menu to the Discord API,
        as well as being able to listen for ``INTERACTION_CREATE`` dispatched
        gateway events.

        The structure of a user context menu:

        .. code-block:: python

            @user_command(name="Context menu name")
            async def context_menu_name(ctx):
                ...

        The ``scope`` kwarg field may also be used to designate the command in question
        applicable to a guild or set of guilds.

        :param name: The name of the application command.
        :type name: Optional[str]
        :param scope?: The "scope"/applicable guilds the application command applies to. Defaults to ``None``.
        :type scope: Optional[Union[int, Guild, List[int], List[Guild]]]
        :param default_permission?: The default permission of accessibility for the application command. Defaults to ``True``.
        :type default_permission: Optional[bool]
        :return: A callable response.
        :rtype: Callable[..., Any]
        """

        def decorator(coro: Coroutine) -> Callable[..., Any]:
            if not len(coro.__code__.co_varnames):
                raise InteractionException(
                    11,
                    message="Your command needs at least one argument to return context.",
                )

            commands: List[ApplicationCommand] = command(
                type=ApplicationCommandType.USER,
                name=name,
                scope=scope,
                default_permission=default_permission,
            )

            if self._automate_sync:
                if self._loop.is_running():
                    [self._loop.create_task(self._synchronize(command)) for command in commands]
                else:
                    [
                        self._loop.run_until_complete(self._synchronize(command))
                        for command in commands
                    ]

            return self.event(coro, name=f"command_{name}")

        return decorator

    def component(self, component: Union[str, Button, SelectMenu]) -> Callable[..., Any]:
        """
        A decorator for listening to ``INTERACTION_CREATE`` dispatched gateway
        events involving components.

        The structure for a component callback:

        .. code-block:: python

            # Method 1
            @component(interactions.Button(
                style=interactions.ButtonStyle.PRIMARY,
                label="click me!",
                custom_id="click_me_button",
            ))
            async def button_response(ctx):
                ...

            # Method 2
            @component("custom_id")
            async def button_response(ctx):
                ...

        The context of the component callback decorator inherits the same
        as of the command decorator.

        :param component: The component you wish to callback for.
        :type component: Union[str, Button, SelectMenu]
        :return: A callable response.
        :rtype: Callable[..., Any]
        """

        def decorator(coro: Coroutine) -> Any:
            payload: str = (
                _component(component).custom_id
                if isinstance(component, (Button, SelectMenu))
                else component
            )
            return self.event(coro, name=f"component_{payload}")

        return decorator

    def autocomplete(
        self, name: str, command: Union[ApplicationCommand, int, str, Snowflake]
    ) -> Callable[..., Any]:
        """
        A decorator for listening to ``INTERACTION_CREATE`` dispatched gateway
        events involving autocompletion fields.

        The structure for an autocomplete callback:

        .. code-block:: python

            @autocomplete("option_name")
            async def autocomplete_choice_list(ctx, user_input: str = ""):
                await ctx.populate([...])

        :param name: The name of the option to autocomplete.
        :type name: str
        :param command: The command, command ID, or command name with the option.
        :type command: Union[ApplicationCommand, int, str, Snowflake]
        :return: A callable response.
        :rtype: Callable[..., Any]
        """

        if isinstance(command, ApplicationCommand):
            _command: Union[Snowflake, int] = command.id
        elif isinstance(command, str):
            _command_obj = self._http.cache.interactions.get(command)
            if not _command_obj:
                _sync_task = ensure_future(self.synchronize(), loop=self.loop)
                while not _sync_task.done():
                    pass  # wait for sync to finish
                _command_obj = self._http.cache.interactions.get(command)
                if not _command_obj:
                    raise InteractionException(6, message="The command does not exist")
            _command: Union[Snowflake, int] = int(_command_obj.id)
        elif isinstance(command, int) or isinstance(command, Snowflake):
            _command: Union[Snowflake, int] = int(command)
        else:
            raise ValueError(
                "You can only insert strings, integers and ApplicationCommands here!"
            )  # TODO: move to custom error formatter

        def decorator(coro: Coroutine) -> Any:
            return self.event(coro, name=f"autocomplete_{_command}_{name}")

        return decorator

    def modal(self, modal: Union[Modal, str]) -> Callable[..., Any]:
        """
        A decorator for listening to ``INTERACTION_CREATE`` dispatched gateway
        events involving modals.

        .. error::
            This feature is currently under experimental/**beta access**
            to those whitelisted for testing. Currently using this will
            present you with an error with the modal not working.

        The structure for a modal callback:

        .. code-block:: python

            @modal(interactions.Modal(
                interactions.TextInput(
                    style=interactions.TextStyleType.PARAGRAPH,
                    custom_id="how_was_your_day_field",
                    label="How has your day been?",
                    placeholder="Well, so far...",
                ),
            ))
            async def modal_response(ctx):
                ...

        The context of the modal callback decorator inherits the same
        as of the component decorator.

        :param modal: The modal or custom_id of modal you wish to callback for.
        :type modal: Union[Modal, str]
        :return: A callable response.
        :rtype: Callable[..., Any]
        """

        def decorator(coro: Coroutine) -> Any:
            payload: str = modal.custom_id if isinstance(modal, Modal) else modal
            return self.event(coro, name=f"modal_{payload}")

        return decorator

    def load(
        self, name: str, package: Optional[str] = None, *args, **kwargs
    ) -> Optional["Extension"]:
        r"""
        "Loads" an extension off of the current client by adding a new class
        which is imported from the library.

        :param name: The name of the extension.
        :type name: str
        :param package?: The package of the extension.
        :type package: Optional[str]
        :param \*args?: Optional arguments to pass to the extension
        :type \**args: tuple
        :param \**kwargs?: Optional keyword-only arguments to pass to the extension.
        :type \**kwargs: dict
        :return: The loaded extension.
        :rtype: Optional[Extension]
        """
        _name: str = resolve_name(name, package)

        if _name in self._extensions:
            log.error(f"Extension {name} has already been loaded. Skipping.")
            return

        module = import_module(
            name, package
        )  # should be a module, because Extensions just need to be __init__-ed

        try:
            setup = getattr(module, "setup")
            extension = setup(self, *args, **kwargs)
        except Exception as error:
            del sys.modules[name]
            log.error(f"Could not load {name}: {error}. Skipping.")
            raise error
        else:
            log.debug(f"Loaded extension {name}.")
            self._extensions[_name] = module
            return extension

    def remove(self, name: str, package: Optional[str] = None) -> None:
        """
        Removes an extension out of the current client from an import resolve.

        :param name: The name of the extension.
        :type name: str
        :param package?: The package of the extension.
        :type package: Optional[str]
        """
        try:
            _name: str = resolve_name(name, package)
        except AttributeError:
            _name = name

        extension = self._extensions.get(_name)

        if _name not in self._extensions:
            log.error(f"Extension {name} has not been loaded before. Skipping.")
            return

        try:
            extension.teardown()  # made for Extension, usable by others
        except AttributeError:
            pass

        if isinstance(extension, ModuleType):  # loaded as a module
            for ext_name, ext in getmembers(
                extension, lambda x: isinstance(x, type) and issubclass(x, Extension)
            ):
                self.remove(ext_name)

            del sys.modules[_name]

        del self._extensions[_name]

        log.debug(f"Removed extension {name}.")

    def reload(
        self, name: str, package: Optional[str] = None, *args, **kwargs
    ) -> Optional["Extension"]:
        r"""
        "Reloads" an extension off of current client from an import resolve.

        :param name: The name of the extension.
        :type name: str
        :param package?: The package of the extension.
        :type package: Optional[str]
        :param \*args?: Optional arguments to pass to the extension
        :type \**args: tuple
        :param \**kwargs?: Optional keyword-only arguments to pass to the extension.
        :type \**kwargs: dict
        :return: The reloaded extension.
        :rtype: Optional[Extension]
        """
        _name: str = resolve_name(name, package)
        extension = self._extensions.get(_name)

        if extension is None:
            log.warning(f"Extension {name} could not be reloaded because it was never loaded.")
            self.load(name, package)
            return

        self.remove(name, package)
        return self.load(name, package, *args, **kwargs)

    async def __raw_socket_create(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        This is an internal function that takes any gateway socket event
        and then returns the data purely based off of what it does in
        the client instantiation class.

        :param data: The data that is returned
        :type data: Dict[Any, Any]
        :return: A dictionary of raw data.
        :rtype: Dict[Any, Any]
        """

        return data

    async def __raw_channel_create(self, channel) -> dict:
        """
        This is an internal function that caches the channel creates when dispatched.

        :param channel: The channel object data in question.
        :type channel: Channel
        :return: The channel as a dictionary of raw data.
        :rtype: dict
        """
        self._http.cache.channels.add(Build(id=channel.id, value=channel))

        return channel._json

    async def __raw_message_create(self, message) -> dict:
        """
        This is an internal function that caches the message creates when dispatched.

        :param message: The message object data in question.
        :type message: Message
        :return: The message as a dictionary of raw data.
        :rtype: dict
        """
        self._http.cache.messages.add(Build(id=message.id, value=message))

        return message._json

    async def __raw_guild_create(self, guild) -> dict:
        """
        This is an internal function that caches the guild creates on ready.

        :param guild: The guild object data in question.
        :type guild: Guild
        :return: The guild as a dictionary of raw data.
        :rtype: dict
        """
        self._http.cache.self_guilds.add(Build(id=str(guild.id), value=guild))

        return guild._json


# TODO: Implement the rest of cog behaviour when possible.
class Extension:
    """
    A class that allows you to represent "extensions" of your code, or
    essentially cogs that can be ran independent of the root file in
    an object-oriented structure.

    The structure of an extension:

    .. code-block:: python

        class CoolCode(interactions.Extension):
            def __init__(self, client):
                self.client = client

            @command(
                type=interactions.ApplicationCommandType.USER,
                name="User command in cog",
            )
            async def cog_user_cmd(self, ctx):
                ...

        def setup(client):
            CoolCode(client)
    """

    client: Client

    def __new__(cls, client: Client, *args, **kwargs) -> "Extension":

        self = super().__new__(cls)

        self.client = client
        self._commands = {}
        self._listeners = {}

        # This gets every coroutine in a way that we can easily change them
        # cls
        for name, func in getmembers(self, predicate=iscoroutinefunction):

            # TODO we can make these all share the same list, might make it easier to load/unload
            if hasattr(func, "__listener_name__"):  # set by extension_listener
                func = client.event(
                    func, name=func.__listener_name__
                )  # capture the return value for friendlier ext-ing

                listeners = self._listeners.get(func.__listener_name__, [])
                listeners.append(func)
                self._listeners[func.__listener_name__] = listeners

            if hasattr(func, "__command_data__"):  # Set by extension_command
                args, kwargs = func.__command_data__
                func = client.command(*args, **kwargs)(func)

                cmd_name = f"command_{kwargs.get('name') or func.__name__}"

                commands = self._commands.get(cmd_name, [])
                commands.append(func)
                self._commands[cmd_name] = commands

            if hasattr(func, "__component_data__"):
                args, kwargs = func.__component_data__
                func = client.component(*args, **kwargs)(func)

                component = kwargs.get("component") or args[0]
                comp_name = (
                    _component(component).custom_id
                    if isinstance(component, (Button, SelectMenu))
                    else component
                )
                comp_name = f"component_{comp_name}"

                listeners = self._listeners.get(comp_name, [])
                listeners.append(func)
                self._listeners[comp_name] = listeners

            if hasattr(func, "__autocomplete_data__"):
                args, kwargs = func.__autocomplete_data__
                func = client.autocomplete(*args, **kwargs)(func)

                name = kwargs.get("name") or args[0]
                _command = kwargs.get("command") or args[1]

                _command: Union[Snowflake, int] = (
                    _command.id if isinstance(_command, ApplicationCommand) else _command
                )

                auto_name = f"autocomplete_{_command}_{name}"

                listeners = self._listeners.get(auto_name, [])
                listeners.append(func)
                self._listeners[auto_name] = listeners

            if hasattr(func, "__modal_data__"):
                args, kwargs = func.__modal_data__
                func = client.modal(*args, **kwargs)(func)

                modal = kwargs.get("modal") or args[0]
                modal_name = f"modal_{modal.custom_id}"

                listeners = self._listeners.get(modal_name, [])
                listeners.append(func)
                self._listeners[modal_name] = listeners

        client._extensions[cls.__name__] = self

        return self

    def teardown(self):
        for event, funcs in self._listeners.items():
            for func in funcs:
                self.client._websocket.dispatch.events[event].remove(func)

        for cmd, funcs in self._commands.items():
            for func in funcs:
                self.client._websocket.dispatch.events[cmd].remove(func)

        clean_cmd_names = [cmd[7:] for cmd in self._commands.keys()]
        cmds = filter(
            lambda cmd_data: cmd_data["name"] in clean_cmd_names,
            self.client._http.cache.interactions.view,
        )

        if self.client._automate_sync:
            [
                self.client._loop.create_task(
                    self.client._http.delete_application_command(
                        cmd["application_id"], cmd["id"], cmd["guild_id"]
                    )
                )
                for cmd in cmds
            ]


@wraps(command)
def extension_command(*args, **kwargs):
    def decorator(coro):
        coro.__command_data__ = (args, kwargs)
        return coro

    return decorator


def extension_listener(name=None):
    def decorator(func):
        func.__listener_name__ = name or func.__name__

        return func

    return decorator


@wraps(Client.component)
def extension_component(*args, **kwargs):
    def decorator(func):
        func.__component_data__ = (args, kwargs)
        return func

    return decorator


@wraps(Client.autocomplete)
def extension_autocomplete(*args, **kwargs):
    def decorator(func):
        func.__autocomplete_data__ = (args, kwargs)
        return func

    return decorator


@wraps(Client.modal)
def extension_modal(*args, **kwargs):
    def decorator(func):
        func.__modal_data__ = (args, kwargs)
        return func

    return decorator


@wraps(Client.message_command)
def extension_message_command(*args, **kwargs):
    def decorator(func):
        kwargs["type"] = ApplicationCommandType.MESSAGE
        func.__command_data__ = (args, kwargs)
        return func

    return decorator


@wraps(Client.user_command)
def extension_user_command(*args, **kwargs):
    def decorator(func):
        kwargs["type"] = ApplicationCommandType.USER
        func.__command_data__ = (args, kwargs)
        return func

    return decorator
