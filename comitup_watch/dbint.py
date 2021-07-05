# Copyright (c) 2021 David Steele <dsteele@gmail.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later
# License-Filename: LICENSE


import asyncio
import re
from datetime import datetime
from typing import List, Set

import dbussy
import ravel


class DBInt:
    _cache = {}
    bus = None

    def __init__(self, bus):
        DBInt.bus = bus

    @staticmethod
    async def get_interface(busname, path, interface):
        if (busname, path, interface) not in DBInt._cache:
            intfc = await DBInt.bus[busname][path].get_async_interface(
                interface
            )
            DBInt._cache[(busname, path, interface)] = intfc

        return DBInt._cache[(busname, path, interface)]

    @staticmethod
    async def GetAllDevices():
        intfc = await DBInt.get_interface(
            "org.freedesktop.NetworkManager",
            "/org/freedesktop/NetworkManager",
            "org.freedesktop.NetworkManager",
        )

        result = await intfc.GetAllDevices()
        return result[0]
