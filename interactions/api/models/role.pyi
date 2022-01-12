from typing import Any, Optional

from .misc import DictSerializerMixin, Snowflake
from ..http import HTTPClient

class RoleTags(DictSerializerMixin):
    _json: dict
    bot_id: Optional[Snowflake]
    integration_id: Optional[Snowflake]
    premium_subscriber: Optional[Any]
    def __init__(self, **kwargs): ...

class Role(DictSerializerMixin):
    _json: dict
    _client: HTTPClient
    id: Snowflake
    name: str
    color: int
    hoist: bool
    icon: Optional[str]
    unicode_emoji: Optional[str]
    position: int
    permissions: str
    managed: bool
    mentionable: bool
    tags: Optional[RoleTags]
    def __init__(self, **kwargs): ...
    async def delete(
        self,
        guild_id: int,
        reason: Optional[str] = None,
    ) -> None: ...
    async def modify(
        self,
        guild_id: int,
        name: Optional[str] = None,
        # permissions,
        color: Optional[int] = None,
        hoist: Optional[bool] = None,
        # icon,
        # unicode_emoji,
        mentionable: Optional[bool] = None,
        reason: Optional[str] = None,
    ) -> "Role": ...
