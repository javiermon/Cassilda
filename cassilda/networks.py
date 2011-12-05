"""
Networks controller
===================

This module implements a Networks class that will keep track of 
network addresses. This is used inside cassilda to configure
the addresses of the images and setup firewall rules, and it
is basically a wrapper of the excellent netaddr_ python library

.. _netaddr : http://pypi.python.org/pypi/netaddr

Typical usage:

    >>> from networks import *

    # Create a new Networks() object
    >>> nets = Networks()

    # Register a new network. No other parameter is needed
    # but a simbolic name. The parameters are calculated
    # automatically to generate a class C network 
    >>> net = nets.register_network("first")

    # Show assigned parameters for the network, returned
    # as a dictionary
    >>> net.get_addresses()
    {'broadcast': '192.168.0.255', 'ip': '192.168.0.1', \
'netmask': '255.255.255.0', 'prefixlen': '24', \
'network': '192.168.0.0'}

    # Now register a new host, into the network,
    # If no address is supplied, the next avaliable
    # one is used. Address is returned as a string
    >>> net.register_host("hostname", "eth0")
    ('192.168.0.1', 'de:ad:be:0:0:0')

    # Create a new network and add the host to it
    >>> net2 = nets.register_network("second")

    >>> net2.register_host("hostname", "eth1")
    ('192.168.1.1', 'de:ad:be:1:0:0')

    # How many networks is this host connected to?
    >>> nh = nets.get_networks_by_host("hostname")
    >>> for n in nh: print(n.name)
    first
    second

    # Create a new host connected to the 'first' network
    >>> net.register_host("hostname2", "eth0")
    ('192.168.0.3', 'de:ad:be:0:0:1')

    # Get all the hosts connected to the first network
    >>> net.get_hostnames()
    ['hostname', 'hostname2']

    # Print the network addresses and hosts
    >>> nets
    Network:  first
        Host:  hostname 192.168.0.1 tap0 192.168.0.2 eth0 de:ad:be:0:0:0
        Host:  hostname2 192.168.0.3 tap2 192.168.0.4 eth0 de:ad:be:0:0:1
    Network:  second
        Host:  hostname 192.168.1.1 tap1 192.168.1.2 eth1 de:ad:be:1:0:0
"""

import netaddr
# Following modules are only needed by the Firewall object
import subprocess
import re

class Host:
    """ Represents a host _in a network_, this is, one of the
    interfaces configured in a running/configured image"""
    def __init__(self, name, address, tapdevice, tapaddress, internaldevice,
                                                                macaddress):
        self.address = address
        self.name = name
        self.internaldevice = internaldevice 
        self.tapdevice = tapdevice
        self.tapaddress = tapaddress
        self.macaddress = macaddress
 
class Network:
    """ Represents a network between two or more configured
    or running images"""
    def __init__(self, networks, name):
        """ Constructor is called from Networks.register_network()
        not directly. Receives the networks object in wich it will
        be registered and the simbolic (i.e. 'first', 'second')
        name"""
        self.name = name
        self.networks = networks;
        self.net =  networks.get_next_network()
        self.hosts = []
        # self.nat = False    # Nat is disabled by default
        self.nat = True     # Nat is disabled by default
        self.next_host_address = netaddr.IPAddress(self.net.ip)
        self.next_mac_address = self.get_net_macaddress()

    def get_addresses(self):
        """ Return addresses of this network as a 
        dictionary, comprising ip, network, broadcast
        netmask """
        return { 'ip': str(self.net.ip), 'network': str(self.net.network),
            'broadcast': str(self.net.broadcast),
            'netmask': str(self.net.netmask),
            'prefixlen': str(self.net.prefixlen) }

    def register_host(self, name, internaldevice, address=None):
        """ Register a hostname with the address got from
        get_next_host_address()
        If no address is forced, the host is created with
        the next address avaliable, that is then returned
        """
        if self.get_address_of_host(name):
            raise ValueError("Trying to register the same host twice")
        if address == None:
            a = netaddr.IPAddress(self.next_host_address)
            self.next_host_address += 1
        else:
            a = address
        b = netaddr.IPAddress(self.next_host_address)
        self.next_host_address += 1
        m = str(self.next_mac_address)
        self.next_mac_address.value += 1
        host = Host(name, str(a), "tap" + str(self.networks.tapnumber),
                                        str(b), internaldevice, str(m))
        self.networks.tapnumber += 1
        self.hosts.append(host)
        return str(a), m

    def get_net_macaddress(self):
        """ Return starting mac address for hosts in this network """
        return netaddr.EUI('de-ad-be-' + "%2.2x" %
            int((int(self.net.network)-3232235520)/256) +
            '-00-00', dialect = netaddr.mac_unix)

    def get_address_of_host(self, name):
        """ Returns address of named host in this network """
        host = self.get_host_by_name(name)
        if host:
            return str(host.address)
        return None

    def get_host_by_name(self, name):
        """ Returns Host object for the named host in this network"""
        for host in self.hosts:
            if host.name == name:
                return host
        return None

    def get_hostnames(self):
        """ Return all the hostnames registered to a certain network
        mostly for debugging purposes """
        r = []
        for host in self.hosts:
            r.append(host.name)
        return r

class Networks:
    """ Class that keeps track of all the networks in a
    Cassilda session"""

    def __init__(self):
        """ Networks constructor. Nothing special here """
        self.networks = []
        self.currnet = None
        self.get_next_network(first_address='192.168.0.1')
        # Tapnumber is global and, for the moment "predicted"
        # (this is, we suppose that the only ones creating
        # tap devices in the system are us and thus devices
        # will appear in order
        # TODO: Use the actual tap devices that are created
        # when the UML kernel is launched
        self.tapnumber = 0

    def __check_output(self, *popenargs):
        """ Implementation of the convenient Python3
            subprocess.check_output """
        process = subprocess.Popen(*popenargs, stdout=subprocess.PIPE)
        output, unused_err = process.communicate()
        retcode = process.poll()
        return output
   
    # But what happens if my network is already 192.168.X.0/24 ?
    def conflicting_network(self, net): 
        process = subprocess.Popen(['ip', 'route', 'list'], stdout=subprocess.PIPE)
        output, unused_err = process.communicate()
        retcode = process.poll()
        di = output.find('default via ')
        if di == -1:
            # No default, so no conflict possible 
            return False 
        gwaddr = output[output.find('default via ')+12:-1]
        gwaddr = gwaddr[0:gwaddr.find('dev')-1]
        if net.ip in list(netaddr.IPNetwork(gwaddr+'/24')):
            return  True
        return False

    def get_next_network(self, first_address=None):
        """ Return next address for network. Only called from Network
        object"""
        if first_address:
            self.next_address = netaddr.IPAddress(first_address)
        oldnet = self.currnet
        self.currnet = netaddr.IPNetwork(str(self.next_address) + '/24')
        if self.conflicting_network(self.currnet):
#            There is a conflict between our current'
#            default gw and the one asked'
#            for the guest. never mind,'
#            we just skip to the next avaliable network :)'
            self.next_address += 256
            self.currnet = netaddr.IPNetwork(str(self.next_address) + '/24')
        self.next_address += 256
        return oldnet

    def register_network(self, network_name):
        """ Create new network and register network by address """
        network = Network(self, network_name)   
        self.networks.append(network)
        return network

    def __getitem__(self, key):
        """ Return the network object referenced by name """
        for network in self.networks:
            if network.name == key:
                return network
        return None

    def set_nat_flag(self, network_name, flag=True):
        """ Set the NAT flag in the network specified, so
            a rule for it to be able to connect to the internet
            through the host system will be added when the 
            image is run (by Firewall)
        """ 
        net = self[network_name]
        if net == None:
            raise Exception ("Called set_natting_flag for a network " + 
                network_name + " that was not used in the config for" +
                " any image")
        net.nat = True

    def get_networks_by_host(self, hostname):
        """ Return a network objects array with the networks
        a certain host has been registered with"""
        r = []
        for n in self.networks:
            if n.get_address_of_host(hostname) != None:
                r.append(n)
        return r

    def get_hosts_by_name(self, hostname):
        """ Return all the host objects associated to a name """
        r = []
        for n in self.get_networks_by_host(hostname):
            h = n.get_host_by_name(hostname)
            if h != None:
                r.append(h)
        return r

    def __repr__(self):
        """ Output the network setup """
        rep = ""
        for n in self.networks:
            rep += "Network: " + n.name + "\n"
            for h in n.hosts:
                rep += "    Host: " + " " + h.name + " " + h.address + " " 
                rep += h.tapdevice + " " + h.tapaddress + " " 
                rep += h.internaldevice + " " + h.macaddress + "\n"
        return rep

if __name__ == "__main__":
    import doctest
    doctest.testmod()

