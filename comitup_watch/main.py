import asyncio
import re
from typing import List, Set

import dbussy
import ravel

dev_paths = set()


def add_dev_path(path):
    global dev_paths

    path = path

    if str(path) not in dev_paths:
        dev_paths |= set(str(path))

        ravel.system_bus().listen_signal(
            path=path,
            fallback=False,
            interface="org.freedesktop.NetworkManager.Device.Wireless",
            name="AccessPointAdded",
            func=ap_added_signal,
        )

        ravel.system_bus().listen_signal(
            path=path,
            fallback=False,
            interface="org.freedesktop.NetworkManager.Device.Wireless",
            name="AccessPointRemoved",
            func=ap_removed_signal,
        )


@ravel.signal(name="DeviceAdded", in_signature="o")
async def device_added_signal(path):
    global dev_paths
    # print(path)

    # print("strpath", path)
    add_dev_path(path)


@ravel.signal(name="AccessPointAdded", in_signature="o")
async def ap_added_signal(path):
    await APManager.update_ssid_list()


@ravel.signal(name="DeviceRemoved", in_signature="o")
async def device_removed_signal(path):
    global dev_paths

    if path in dev_paths:
        dev_paths -= set(path)

        ravel.system_bus().unlisten_signal(
            path=path,
            fallback=False,
            interface="org.freedesktop.NetworkManager.Device.Wireless",
            name="AccessPointAdded",
            func=ap_added_signal,
        )


@ravel.signal(name="AccessPointRemoved", in_signature="o")
async def ap_removed_signal(path):
    await APManager.update_ssid_list()


class DBInt:
    _cache = {}

    @staticmethod
    async def get_interface(busname, path, interface):
        if (busname, path, interface) not in DBInt._cache:
            intfc = await ravel.system_bus()[busname][
                path
            ].get_async_interface(interface)
            DBInt._cache[(busname, path, interface)] = intfc

        return DBInt._cache[(busname, path, interface)]


class DeviceMonitor:
    def __init__(self, bus):
        pass

    async def GetAllDevices():
        intfc = await DBInt.get_interface(
            "org.freedesktop.NetworkManager",
            "/org/freedesktop/NetworkManager",
            "org.freedesktop.NetworkManager",
        )
    
        result = await intfc.GetAllDevices()
        return result[0]

class APManager(DBInt):
    _ssids: Set[str] = set()
    _lock: asyncio.locks.Lock = asyncio.Lock()

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

                if not ssid:
                    await asyncio.sleep(1)
                    ssid = (
                        await intfc.Get(
                            "org.freedesktop.NetworkManager.AccessPoint",
                            "Ssid",
                        )
                    )[0][1]
                    ssid = bytearray(ssid).decode()

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
        async with klass._lock:
            await klass._update_ssid_list()

    @classmethod
    async def new_ssid(klass, ssid):
        print("new ssid", ssid)

    @classmethod
    async def lost_ssid(klass, ssid):
        print("lost ssid", ssid)


async def GetAllDevices():
    intfc = await DBInt.get_interface(
        "org.freedesktop.NetworkManager",
        "/org/freedesktop/NetworkManager",
        "org.freedesktop.NetworkManager",
    )

    result = await intfc.GetAllDevices()
    return result[0]


async def main_async(bus):
    print(await GetAllDevices())
    print("running loop")

    for devpath in await GetAllDevices():
        add_dev_path(devpath)

    ravel.system_bus().listen_signal(
        path="/org/freedesktop/NetworkManager",
        fallback=False,
        interface="org.freedesktop.NetworkManager",
        name="DeviceAdded",
        func=device_added_signal,
    )

    ravel.system_bus().listen_signal(
        path="/org/freedesktop/NetworkManager",
        fallback=False,
        interface="org.freedesktop.NetworkManager",
        name="DeviceRemoved",
        func=device_removed_signal,
    )

    await APManager.update_ssid_list()

    while True:
        await asyncio.sleep(1)


def main():
    print("starting")
    loop = asyncio.get_event_loop()

    bus = ravel.system_bus()
    bus.attach_asyncio(loop)

    loop.create_task(main_async(bus))
    loop.run_forever()
