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

from . import devicemon, comitup_mon, avahi_watch


async def main_async(bus):

    comitupmon = comitup_mon.ComitupMon()
    event_queue = comitupmon.event_queue()

    devmon = devicemon.DeviceMonitor(bus, event_queue)
    await devmon.startup()

    avahimon = asyncio.create_task(avahi_watch.amain(event_queue))

    await comitupmon.run()


def main():
    print("starting")
    loop = asyncio.get_event_loop()

    bus = ravel.system_bus()
    bus.attach_asyncio(loop)

    loop.create_task(main_async(bus))
    loop.run_forever()
