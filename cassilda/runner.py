__version__ = "cassilda 0.0.1"

"""
Runner class module
"""
import pexpect
import os
import tempfile
import shutil
from .networks import *
UML = 1

def print_line(line):
    '''Default Runner callback to print a line'''
    print(line)

class Runner:
    ''' An image runner

       This class defines methods that are used by inheritors to implement
       the builder itself
    '''
    def __init__(self, imagepath, kind, networks, hostname,
            kernelpath = None, memory = '128M', log_callback = None):
        ''' Builder constructor, receiving a callback to receive
        lines printed by this module
        '''
        self.imagepath = imagepath
        self.kernelpath = kernelpath
        self.memory = memory
        self.hosts = networks.get_hosts_by_name(hostname)
        if not os.path.exists(imagepath):
            raise ValueError("The image passed to the runner does not exist")
        self.process = None

    def log(self, line):
        self.log_callback(line)

    def run(self, termnum):
        d, m = divmod(termnum, 2)
        if m:
            x = 486
        else:
            x = 0
        y = d * 256

        commandline = "./" + self.kernelpath + " " + "ubd0="
        commandline += self.imagepath + " mem=" + self.memory + " "

        for h in self.hosts:
            commandline += h.internaldevice + "=tuntap," 
            commandline += h.tapdevice + "," + str(h.tapaddress) + " "

        commandline += " con0=fd:0,fd:1"
        print ("About to spawn this: %s" % commandline)
        self.sp = pexpect.spawn(commandline)

    def running(self):
        if self.sp == None:
            return False
        return self.sp.isalive()

    def interact(self):
        self.sp.interact()

    def shutdown(self):
        """ Log as root in the image and perform a shutdown -h now """
 

