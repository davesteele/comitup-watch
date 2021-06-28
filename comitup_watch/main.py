import asyncio
import re
from datetime import datetime
from typing import List, Set

import dbussy
import ravel

from . import devicemon


async def main_async(bus):

    devmon = devicemon.DeviceMonitor(bus)
    await devmon.startup()

    while True:
        await asyncio.sleep(1)


def main():
    print("starting")
    loop = asyncio.get_event_loop()

    bus = ravel.system_bus()
    bus.attach_asyncio(loop)

    loop.create_task(main_async(bus))
    loop.run_forever()
