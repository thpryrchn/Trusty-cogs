from abc import ABC, abstractmethod
from typing import List
from aiohttp import ClientSession

import discord
from redbot.core import Config
from redbot.core.bot import Red


class MixinMeta(ABC):
    """
    Metaclass for well behaved type hint detection with composite class.
    """
    # https://github.com/mikeshardmind/SinbadCogs/blob/v3/rolemanagement/abc.py
    # https://github.com/python/mypy/issues/1996

    def __init__(self, *_args):
        self.config: Config
        self.bot: Red
        self.session: ClientSession
