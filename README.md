
# Comitup-Watch

## Monitor local Comitup-enabled Devices

![Comitup-Watch Screenshot](https://davesteele.github.io/comitup-watch/images/comitup-watch.png)


[Comitup](https://davesteele.github.io/comitup/) is a package that allows you to bootstrap headless devices on to the Internet via WiFi. Comitup-Watch lets you see the status of pending and connected Comitup-enabled devices on your local network.

## Man Page


### NAME

comitup-watch -- monitor local Comitup-enabled devices

#### SYNOPSIS

    $ `comitup-watch`

#### DESCRIPTION

The **comitup-watch** program is a terminal utility that displays the status of
local WiFi Access Points and network host names/ip addresses. It is targeted
for showing the status of devices running the _Comitup_ service.

The program collects information from a number of sources, and displays in a
series of columns:

  * __SSID__

    The name of a visible WiFi Access Point. A Comitup-enabled device will
    create an Access Point whenever it is unsuccessful in making an established
    WiFi connection. Once a user connects to this AP, a captive portal enables
    the definition of a connection for the current environment.

    A Comitup device with two WiFi interfaces, running in _appliance mode_, can
    show both an active SSID and local network information at the same time.

    SSID information is collected from **NetworkManager**.

    The accuracy of thie column is improved if there is an unconnected WiFi
    interface available.

  * __Domain Name__

    The fully qualified domain name for the device. Any system which supports
    mdns can use this name to access the device.

    The domain name, and the IP address columns, are extracted from a
    Comitup-published Avahi/ZeroConf service. Data in these columns indicates
    that the device is accessible on the network.

  * __IPv4__

    An accessible IPv4 address for the device.

  * __IPv6__

    An accessible IPv6 address for the device. Recent Comitup versions by
    default create only link-local IPv6 addresses for controlled WiFi
    connections.

  * __Ping__

    The program will periodically attempt to ping devices with known addresses.
    This column displays the latest result for that test.

Recent information in the table is shown in green.

#### COPYRIGHT

Comitup-watch is Copyright (C) 2021 David Steele &lt;steele@debian.org&gt;

#### SEE ALSO

[comitup(8)](https://davesteele.github.io/comitup/man/comitup.pdf)
