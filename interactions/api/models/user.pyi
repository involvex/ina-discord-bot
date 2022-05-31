from typing import Optional, Union

from .misc import DictSerializerMixin, Snowflake
from .flags import UserFlags

class User(DictSerializerMixin):
    _json: dict
    id: Snowflake
    username: str
    discriminator: str
    avatar: Optional[str]
    bot: Optional[bool]
    system: Optional[bool]
    mfa_enabled: Optional[bool]
    banner: Optional[str]
    accent_color: Optional[int]
    banner_color: Optional[str]
    locale: Optional[str]
    verified: Optional[bool]
    email: Optional[str]
    flags: Optional[UserFlags]
    premium_type: Optional[int]
    public_flags: Optional[UserFlags]
    def __init__(self, **kwargs): ...
    def __repr__(self) -> str: ...
    def has_public_flag(self, flag: Union[UserFlags, int]) -> bool: ...
    @property
    def mention(self) -> str: ...
    @property
    def avatar_url(self) -> str: ...
    @property
    def banner_url(self) -> Optional[str]: ...
