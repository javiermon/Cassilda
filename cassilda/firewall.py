"""
Firewall interface 
==================

Highly coupled with the Networks object, sets up rules to
allow the image to connect with the host network and to internet
"""

from . import networks
import subprocess
import os

class Firewall:
    def __init__(self, networks):
        self.networks = networks
        self.__set_forwarding(True)
        # Keep track of an array of pairs [network, refcount]
        # to know when to set/unset natting rules for a certain
        # network
        self.nat_rules = []

    # Next function was shamelessly copied from NetCommander code
    def __set_forwarding(self, status):
        """ Set forwarding flag in the kernel """
        if not os.path.exists( '/proc/sys/net/ipv4/ip_forward' ):
            raise Exception( "'/proc/sys/net/ipv4/ip_forward' " + 
                "not found, this is not a compatible operating system." )

        fd = open( '/proc/sys/net/ipv4/ip_forward', 'w+' )
        fd.write( '1' if status == True else '0' )
        fd.close()

    def __set_proxyarp(self, tapdevice, status):
        path = '/proc/sys/net/ipv4/conf/' + tapdevice + '/proxy_arp'
        if not os.path.exists(path):
            raise Exception( "The device " + tapdevice + " does not exist")
        fd = open( path, 'w+' )
        fd.write( '1' if status == True else '0' )
        fd.close()

    def __check_output(self, *popenargs):
        """ Implementation of the convenient Python3
            subprocess.check_output """
        process = subprocess.Popen(*popenargs, stdout=subprocess.PIPE)
        output, unused_err = process.communicate()
        retcode = process.poll()
        return output
 
    def __waniface(self):
        """ quick and dirty way to guess the wan interface of a
        linux host"""
        s = self.__check_output(["ip", "route", "list"]).decode("utf-8")
        i = s.find('default')
        if i == -1:
            raise ValueError("No default WAN interface found")
        eol = s.find('\n', i)
        if i == -1:
            raise ValueError("No default WAN interface found")
        dev = s.find('dev', i, eol)
        if i == -1:
            raise ValueError("No default WAN interface found")
        end = s.find(' ', dev + 4)
        return s[dev + 4:end]

    def __create_tuntap(self, h):
        subprocess.call("tunctl -t " + h.tapdevice, shell=True)
        subprocess.call("ifconfig " + h.tapdevice + " " + str(h.tapaddress),
                                                    shell=True)
        self.__set_proxyarp(h.tapdevice, True)

    def __delete_tuntap(self, h):
        self.__set_proxyarp(h.tapdevice, False)
        subprocess.call("tunctl -d " + h.tapdevice, shell=True)
        subprocess.call("ifconfig " + h.tapdevice + " down", shell=True)
 
    def __accept_tap_rule(self, h):
        """ Return the accept tap rule for a certain host
        as a string"""
        return "iptables -t nat -I PREROUTING -i " + \
            h.tapdevice + " -j ACCEPT" 
        
    def __masquerade_tap_rule(self, h, n, delete=False):
        """ Return the masquerade tap rule as a string"""
        netdict = n.get_addresses()
        rule = "iptables -t nat "
        if delete:
            rule += "-D "
        else:
            rule += "-I "
        rule += ("POSTROUTING -s " + netdict['network'] + "/" +
                netdict['prefixlen'] + " -o " + self.__waniface() +
                " -j MASQUERADE")
        return rule

    def __routing_rule(self, h, delete=False):
        """ Return a string with a suitable routing route(8) rule to
            allow packages to reach the host through the assigned
            tap iface """
        rule = "route "
        if delete:
            rule += "del "
        else:
            rule += "add "
        rule += h.address + " dev " + h.tapdevice
        return rule

    def __retrieve_network_and_host_objects(self, network, host):
        """ Convenience function to retrieve objects from the
            networks controller"""
        n = self.networks[network]
        if n == None:
            raise ValueError("No network with name " + network + " found")
        h = n.get_host_by_name(host)
        if h == None:
            raise ValueError("No host with name " + host + 
                            " found in network " + network)
        return n, h

    def __get_nat_rule(self, network):
        for n, r in self.nat_rules:
            if n == network:
                return r
        return 0

    def __add_nat_rule(self, network):
        count = self.__get_nat_rule(network)
        if count != 0:
            self.nat_rules.remove([network, count])
        self.nat_rules.append([network, count + 1])
        return count

    def __del_nat_rule(self, network):
        count = self.__get_nat_rule(network)
        if count == 0:
            raise Exception('Called __del_nat_rule for a network that ' +
                'does not exist yet: ' + network)
        self.nat_rules.remove([network, count])
        if count > 1:
            self.nat_rules.append([network, count -1])
        return count

    def set_iface(self, network, host):
        """ Setup the interface retrieving the associated Network 
        object """
        n, h = self.__retrieve_network_and_host_objects(network, host)
        self.__create_tuntap(h)
    #   l1 = eval(self.__accept_tap_rule(h))
    #   l2 = eval(self.__masquerade_tap_rule(h, n))
    #   Do not call the accept tap rule "a ver que pasa"
    #   subprocess.call(self.__accept_tap_rule(h), shell=True)
        if n.nat: 
            if self.__add_nat_rule(network) == 0:
                r = self.__masquerade_tap_rule(h, n)
                print('set_iface(): Setting rule ' + r)
                subprocess.call(r, shell=True)
        n, h = self.__retrieve_network_and_host_objects(network, host)
        routing_rule = self.__routing_rule(h)
        print("set_iface_postrun: about to call: " + routing_rule)
        subprocess.call(routing_rule, shell=True)

    def unset_iface(self, network, host):
        """ Delete the rules set up by set_iface() """
        n, h = self.__retrieve_network_and_host_objects(network, host)
        subprocess.call(self.__routing_rule(h, delete=True), shell=True)
        if n.nat:
            refcount = self.__del_nat_rule(network)
            print 'self.__del_nat_rule(' + network + ') = ' + str(refcount)
            if refcount == 1:
                derouting_rule = self.__masquerade_tap_rule(h, n, delete=True)
                print("unset_iface: about to call: " + derouting_rule)
                subprocess.call(derouting_rule, shell=True)
        self.__delete_tuntap(h)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

