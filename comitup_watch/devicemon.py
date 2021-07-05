# Copyright (c) 2021 David Steele <dsteele@gmail.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later
# License-Filename: LICENSE


import asyncio
import re
from datetime import datetime
from enum import Enum
from typing import List, NamedTuple, Set

import dbussy
import ravel

from .dbint import DBInt


class DeviceMonAction(Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"


class DeviceMonMsg(NamedTuple):
    action: DeviceMonAction
    ssid: str


class DeviceMonitor(DBInt):
    def __init__(self, bus, event_queue):
        self.dev_paths = set()

        self.event_queue = event_queue
        APManager.event_queue = event_queue

        super().__init__(bus)

    async def startup(self) -> None:
        for devpath in await self.GetAllDevices():
            print(devpath)
            await self.add_dev_path(devpath)

        DBInt.bus.listen_signal(
            path="/org/freedesktop/NetworkManager",
            fallback=False,
            interface="org.freedesktop.NetworkManager",
            name="DeviceAdded",
            func=self.device_added_signal,
        )

        DBInt.bus.listen_signal(
            path="/org/freedesktop/NetworkManager",
            fallback=False,
            interface="org.freedesktop.NetworkManager",
            name="DeviceRemoved",
            func=self.device_removed_signal,
        )

        await APManager.update_ssid_list()

    async def add_dev_path(self, path):

        print("Added device path", path)

        if str(path) not in self.dev_paths:
            self.dev_paths |= set(str(path))

            DBInt.bus.listen_signal(
                path=path,
                fallback=False,
                interface="org.freedesktop.NetworkManager.Device.Wireless",
                name="AccessPointAdded",
                func=self.ap_added_signal,
            )

            DBInt.bus.listen_signal(
                path=path,
                fallback=False,
                interface="org.freedesktop.NetworkManager.Device.Wireless",
                name="AccessPointRemoved",
                func=self.ap_removed_signal,
            )

    @ravel.signal(name="DeviceAdded", in_signature="o")
    async def device_added_signal(self, path):
        # print(path)

        # print("strpath", path)
        await self.add_dev_path(path)

    @ravel.signal(name="DeviceRemoved", in_signature="o")
    async def device_removed_signal(self, path):

        print("Removing device path", path)

        if str(path) in self.dev_paths:

            self.dev_paths -= set(path)

            DBInt.bus().unlisten_signal(
                path=path,
                fallback=False,
                interface="org.freedesktop.NetworkManager.Device.Wireless",
                name="AccessPointAdded",
                func=self.ap_added_signal,
            )

    @ravel.signal(name="AccessPointAdded", in_signature="o")
    async def ap_added_signal(self, path):
        await APManager.update_ssid_list()

    @ravel.signal(name="AccessPointRemoved", in_signature="o")
    async def ap_removed_signal(self, path):
        await APManager.update_ssid_list()


class APManager(DBInt):
    _ssids: Set[str] = set()
    _lock: asyncio.locks.Lock = asyncio.Lock()
    _waiting: bool = False
    event_queue = None

    @classmethod
    async def update_ap_paths(klass) -> List[str]:
        """Get a full list of AccessPoint paths in NM, by hook or crook."""

        intfc = await klass.get_interface(
            "org.freedesktop.NetworkManager",
            "/org/freedesktop/NetworkManager/AccessPoint",
            "org.freedesktop.DBus.Introspectable",
        )
        introspect = (await intfc.Introspect())[0]

        lines = [x for x in introspect.split("\n") if "node name" in x]
        nums = [
            re.search(
                '"(.+)"',
                x,
            ).group(1)
            for x in lines
        ]
        paths = [
            "/org/freedesktop/NetworkManager/AccessPoint/" + x for x in nums
        ]

        return paths

    @classmethod
    async def new_ssid_list(klass):
        """Get a current list of SSIDs per the current NM AccessPoint's."""

        ssids = set()
        for ap_path in await klass.update_ap_paths():
            intfc = await klass.get_interface(
                "org.freedesktop.NetworkManager",
                ap_path,
                "org.freedesktop.DBus.Properties",
            )

            try:
                ssid = (
                    await intfc.Get(
                        "org.freedesktop.NetworkManager.AccessPoint", "Ssid"
                    )
                )[0][1]
                ssid = bytearray(ssid).decode()

                if ssid:
                    ssids |= set([ssid])
            except dbussy.DBusError:
                pass

        return ssids

    @classmethod
    async def _update_ssid_list(klass):
        """Find changes in the SSID space, w/ callbacks indicating changes."""
        new_list = await klass.new_ssid_list()

        new_ssids = new_list - klass._ssids
        for new_ssid in new_ssids:
            await klass.new_ssid(new_ssid)

        klass._ssids |= new_ssids

        lost_ssids = klass._ssids - new_list
        for lost_ssid in lost_ssids:
            await klass.lost_ssid(lost_ssid)

        klass._ssids -= lost_ssids

    @classmethod
    async def update_ssid_list(klass):
        """Wrap the SSID update call with an asyncio Lock."""

        if klass._waiting:
            return

        print("updating ssid_list")

        klass._waiting = True
        async with klass._lock:
            await asyncio.sleep(0.5)
            klass._waiting = False

            await klass._update_ssid_list()

    @classmethod
    async def new_ssid(klass, ssid):
        print("new ssid", ssid)
        msg = DeviceMonMsg(DeviceMonAction.ADDED, ssid)
        await klass.event_queue.put(msg)

    @classmethod
    async def lost_ssid(klass, ssid):
        print("lost ssid", ssid)
        msg = DeviceMonMsg(DeviceMonAction.REMOVED, ssid)
        await klass.event_queue.put(msg)
