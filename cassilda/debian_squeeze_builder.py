__version__ = "cassilda 0.0.1"

"""
Debian Squeeze builder
"""

import time

from .builder import Builder
from .networks import Network

class debian_squeeze_Builder(Builder):
    buildertype = 'debian_squeeze'
    def __init__(self, callback = None, repository = None):
        """ Constructor. Receives the callback for logs and the repo URL """
        Builder.__init__(self, callback)
        if repository == None:
            self.repo = "http://127.0.0.1:3142/ftp.fi.debian.org/debian"
        else:
            self.repo = repository

    def build_image(self, image, repository, size):
        """ Build the image """
        self.create_image(image.imagename, size)
        self.make_filesystem(image.imagename)
        r = self.install(image.packages, image.basename, image.imagename,
                                                        repository)
        if not r:
            return False
        self.set_hostname(image.name, image.imagename)
        return True 

    def set_hostname(self, hostname, imagepath):
        """ Set hostname in debian putting it in /etc/hostname """
        self.log("Setting hostname to " + hostname)
        self.mount_filesystem(imagepath)
        self.append_to_file("/etc/hostname", hostname, overwrite=True)
        self.umount_filesystem()

    def set_repository(self, imagepath, address):
        self.mount_filesystem(imagepath)
        self.replace_in_file("/etc/apt/sources.list", "127.0.0.1", address)
        self.umount_filesystem()

    def set_network(self, imagepath, address, netmask, network, broadcast,
                                                gateway, internaldevice):
        """ Set network in debian putting its parameters in
        /etc/network/interfaces """
        self.mount_filesystem(imagepath)
        if internaldevice == "eth0":
            iz = 'auto lo\n\niface lo inet loopback\n\n'
            overwrite=True
        else:
            iz = ''
            overwrite=False

        iz += "auto " + internaldevice + "\n"
        iz += "iface " + internaldevice + " inet static\n"
        iz += "\taddress " + address + "\n"
        iz += "\tnetmask " + netmask + "\n"
        iz += "\tnetwork " + network + "\n"
        iz += "\tbroadcast " + broadcast + "\n"
        if gateway:
            iz += "\tgateway " + gateway + "\n"
        
        self.append_to_file("/etc/network/interfaces", iz, overwrite)
        self.umount_filesystem()

    def set_mac_address(self, imagepath, interface, mac_address):
        """ Setup the mac address of an interface so it is the same
            between reboots """
        self.mount_filesystem(imagepath)
        self.log("Setting mac address of interface " + interface +
                                                " to " + mac_address)
        rulestring = 'SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", '
        rulestring += 'ATTR{address}=="' + mac_address 
        rulestring += '", ATTR{dev_id}=="0x0", ' 
        rulestring += 'ATTR{type}=="1", KERNEL=="eth*", NAME="'
        rulestring += interface + '"'
        self.append_to_file("/etc/udev/rules.d/70-persistent-net.rules",
                                                            rulestring)
        self.umount_filesystem()

    def install_image(self, packages, imagename, repository):
        """ Actually install the image, debootstrapping it and
        installing the packages"""

        self.mount_filesystem(imagename)
        self.create_dir("/root/.ssh")
        self.create_dir("/etc")
        self.append_to_file("/etc/hosts", "127.0.0.1 localhost\n")

        self.repo = repository
        try:
            self.log("Debootstraping the distributon...") 
            self.call(["debootstrap", "--arch", "i386",
                "squeeze", self.mountdir,
                self.repo])
            ret = True
        except:
            self.log("Error while trying to debootstrap. No net?")
            self.umount_filesystem()
            return False

        self.mount_sys_and_dev()

        self.append_to_file("/install_things.sh", "#!/bin/bash\n" +
            "export LC_ALL=C\n" +
            "aptitude -y update\n" +
            "aptitude -y install " + packages + "\n" +
            "echo StrictHostKeyChecking no >> /etc/ssh/ssh_config\n")
        
        self.chmod("/install_things.sh", 0o744)

        self.log("Installing the packages via chroot...") 
        self.call(["chroot", self.mountdir, "/install_things.sh"])
        self.log("Last settings (change root password, set prompt, etc)")
        self.append_to_file("/root/.bashrc", "export PS1='" +
                imagename + " \w \\$ '")
        self.append_to_file("/etc/skel/.bashrc", "export PS1='" + 
                imagename + " \w \\$ '")

        self.append_to_file("/change_root_password.sh", 
            '#!/bin/bash\necho -e "root\\nroot" | passwd root\n')
        self.chmod("/change_root_password.sh", 0o744)
        s = self.call(["chroot", self.mountdir, "/change_root_password.sh"])
        
        self.append_to_file("/etc/fstab","/dev/udb0 / ext2 defaults 0 0\n" +
            "proc      /proc proc defaults 0 0\n")
        
        self.append_to_file("/etc/inittab",
            "#minimal inittab taken from some uml tutorial\n"+
            "id:2:initdefault:\n"+
            "si::sysinit:/etc/init.d/rcS\n"+
            "~~:S:wait:/sbin/sulogin\n"+
            "l0:0:wait:/etc/init.d/rc 0\n"+
            "l1:1:wait:/etc/init.d/rc 1\n"+
            "l2:2:wait:/etc/init.d/rc 2\n"+
            "l3:3:wait:/etc/init.d/rc 3\n"+
            "l4:4:wait:/etc/init.d/rc 4\n"+
            "l5:5:wait:/etc/init.d/rc 5\n"+
            "l6:6:wait:/etc/init.d/rc 6\n"+
            "z6:6:respawn:/sbin/sulogin\n"+
            "ca:12345:ctrlaltdel:/sbin/shutdown\n"+
            "pf::powerwait:/etc/init.d/powerfail start\n"+
            "pn::powerfailnow:/etc/init.d/powerfail now\n"+
            "po::powerokwait:/etc/init.d/powerfail stop\n"+
            "c0:2345:respawn:/sbin/getty 38400 tty0 linux\n", overwrite=True)

        self.append_to_file("/etc/securetty", 
            "console\n" +
            "tty0\n" +
            "ttyS0\n")

        # MARK
        self.umount_sys_and_dev()
        self.umount_filesystem()
        return ret

