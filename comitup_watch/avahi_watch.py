

from zeroconf import Zeroconf, ServiceBrowser

class MyListener:
    def __init__(self, zc):
        self.zc = zc

    def remove_service(self, zeroconf, tipe, name):
        print("Removed - {}".format(name))

    def add_service(self, zeroconf, tipe, name):
        print("Added - {}".format(name))

        si = zc.get_service_info("_comitup._tcp.local.", name)

        print("    {}".format(si.parsed_addresses()))
        print("    {}".format(si.get_name()))

    def update_service(self, *args, **kwargs):
        pass

zc = Zeroconf()
listener = MyListener(zc)
browser = ServiceBrowser(zc, "_comitup._tcp.local.", listener)

try:
    input("")
finally:
    zeroconf.close()
