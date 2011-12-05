__version__ = "cassilda 0.0.1"

"""
Module defining the Cassilda class

See README for details
"""
import yaml
import os
import time
import tempfile
import urllib
import bz2
import inspect

from .image import Image
from .builder import Builder
from .debian_squeeze_builder import debian_squeeze_Builder
from .networks import Networks
from .firewall import Firewall
from .runner import *

# Convenient classes to handle YAML document types
class ImageLoader(yaml.YAMLObject):
    yaml_tag = u'!image'
    def __init__(self, name, size, memory, networks, builder, packages,
            installer, test):
        args, _, _, values = inspect.getargvalues(inspect.currentframe())
        for i in args:
            self.__dict__[i] = values[i]

class GeneralLoader(yaml.YAMLObject):
    yaml_tag = u'!general'
    def __init__(self, description, repository, kernel, default_packages):
        args, _, _, values = inspect.getargvalues(inspect.currentframe())
        for i in args:
            self.__dict__[i] = values[i]

class DocumentationLoader(yaml.YAMLObject):
    yaml_tag = u'!documentation'
    def __init__(self, kind, markup):
        self.kind = kind
        self.markup = markup

class IncludeLoader(yaml.YAMLObject):
    yaml_tag = u'!include'
    def __init__(self, include):
        self.include = include

    def load_docs(self, cas, includepaths):
        """ Load all docs in all the included files,
            parsing them by calling the parse_yaml_doc()
            function of the 'parent' cassilda
        """
        for filename in self.include:
            # Append the filename to the includepaths and
            # check for an existing file in order
            for includepath in includepaths:
                fullpath = includepath + filename
                if os.path.exists(fullpath):
                   break
                else:
                    fullpath = None
            if not fullpath:
                raise Exception("included file wasn't found in the" +
                        " includepaths: " + filename)
            # print('Including yaml from %s' % fullpath)
            f = open(fullpath, 'r')
            s = f.read()
            f.close()
            for data in yaml.load_all(s):
                cas.parse_yaml_doc(data, includepaths)

# class Installer(name, description, install, uninstall, run, stop)
class InstallerLoader(yaml.YAMLObject):
    yaml_tag = u'!installer'
    def __init__(self, name, description, install, uninstall, run, stop):
        args, _, _, values = inspect.getargvalues(inspect.currentframe())
        for i in args:
            self.__dict__[i] = values[i]

class NetworksLoader(yaml.YAMLObject):
    yaml_tag = u'!networks'
    def __init__(self, networks):
        self.networks = networks

class Installer():
    def __init__(self, image, name, description, install, uninstall, run, stop):
        args, _, _, values = inspect.getargvalues(inspect.currentframe())
        for i in args:
            self.__dict__[i] = values[i]

    def login(self):
        if self.logged:
            return True
        self.image.sp.sendline('')
        self.image.sp.expect('login: ')
        self.image.sp.sendline('root')
        self.image.sp.expect('Password: ')
        self.image.sp.sendline('root')
        self.image.sp.expect('# ')
        self.logged = True

    def logout(self):
        if not self.logged:
            return True
        self.image.sp.sendline('')
        self.image.sp.expect('# ')
        self.image.sp.sendline('logout')
        self.image.sp.expect('login: ')
        self.logged = False

    def halt(self):
        self.login()

class Cassilda:
    """
    Cassilda represents a group of images with it's settings
    and eventually some tests
    """
    def __init__(self, path, includepaths):
        """ Cassilda constructor. Path must point to a valid 
        cassilda configuration file in YAML format"""
        self.d = None;
        self.networks = Networks()
        self.images = []
        self.installers = []
        f = open(path, 'r')
        s = f.read()
        f.close()
        for data in yaml.load_all(s):
            self.parse_yaml_doc(data, includepaths)
        self.parse_installers()
        self.firewall = Firewall(self.networks)
        return None

    def parse_installers(self):
        for i in self.images:
            if i.installer == None:
                print('Note that image ' + i.name + 'dont have installers')
                return
            for n in i.installer:
                # print('image ' + i.name + ' installer ' + n)
                il = self.__get_installer_loader_from_name(n)
                if il == None:
                    raise Exception('Specificed installer ' + n +
                        ' not found')
                image_installer = self.process_installer(i, il)
                i.installers.append(image_installer)

    def process_installer(self, image, il):
        installer = Installer(image, il.name, il.description, 
            self.process_code(il.install), self.process_code(il.uninstall),
            self.process_code(il.run), self.process_code(il.stop))
        return installer

    # Return an array containing pexpect 'expect() and call()'
    # arguments
    def process_code(self, code):
        r = []
        t = {}
        t['expect-before'] = [ None, 0 ]
        t['call'] = code
        t['expect-after'] =  [ None, 0 ]
        r.append(t)
        return r

    def parse_yaml_doc(self, data, includepaths):
            if data.__class__ == ImageLoader:
                # print("ImageLoader: %s" % data.name)
                dir(data)
                im = Image(data.name, data.size, data.memory,
                                data.builder, data.packages,
                                data.installer)
                # Set networks
                devn = 0
                try:
                    for n in data.networks:
                        net = self.networks[n]
                        if net == None:
                            net = self.networks.register_network(n)
                        net.register_host(im.name, "eth" + str(devn))
                        devn += 1
                except KeyError:
                    # No networks configured for this image
                    print("No networks found in image ", im.name)
                except:
                    raise
                self.images.append(im)
            elif data.__class__ == GeneralLoader:
                # print("GeneralLoader.repository: %s" % data.repository)
                self.kernelurl = data.kernel 
                self.repository = data.repository
            elif data.__class__ == DocumentationLoader:
                self.documentation = data.markup
            elif data.__class__ == IncludeLoader:
                data.load_docs(self, includepaths)
            elif data.__class__ == InstallerLoader:
                # print("InstallerLoader.name: %s description %s" % (data.name,
                #                data.description))
                self.installers.append(data)
            """
            elif data.__class__ == NetworksLoader:
                print("InstallerLoader.networks %s" % data.networks)
                self.networks.append(data)
            """

    def build_all(self):
        """ Install all images in the .cassilda """
        for i in self.images:
            self.build(i.name)

    def build(self, name):
        """ Build and configure networks/etc for the image referenced
            by name from the cassilda configuration file"""
        if not os.geteuid() == 0:
            raise Exception("Only root can run this (yet)")
        i = self[name]
        if i == None:
            raise Exception('Image ' + name + ' is not in the profile')
        print("install_and_configure: Building image ", i.name)
        # builder = Builder.build(i, self.repository)
        builder = debian_squeeze_Builder() 
        if builder == None:
            return False
        b = builder.build(i, self.repository, i.size)
        for n in self.networks.get_networks_by_host(name):
            h = n.get_host_by_name(name)
            a = n.get_addresses()
            print("Setting up host ", name, " with address "
                , h.address," into network ", a)
            builder.set_network(i.imagename, str(h.address),
                    a['netmask'], a['network'], a['broadcast'],
                    str(h.tapaddress), h.internaldevice)
            print("Setting up mac address of host device ",
                    h.internaldevice, "with mac address ",
                    h.macaddress)
            builder.set_mac_address(i.imagename, h.internaldevice,
                    h.macaddress)
        # Set sources.list with the ip of the first network
        # found for the image
        h = self.networks.get_networks_by_host(name)[0].get_host_by_name(name)
        builder.set_repository(i.imagename, str(h.tapaddress))

    def install(self, name):
        i = self[name]
        if i == None:
            raise Exception('Image ' + name + ' is not in the profile')
        self.run(name)
        for ins in i.installers:
            print('install: Installing ' + ins.name + ' into ' + i.name)

    def __get_installer_loader_from_name(self, installer_name):
        for i in self.installers:
            if i.name == installer_name:
                return i
        return None

    def __getitem__(self, image_name):
        """ Return the network object referenced by name """
        for image in self.images:
            if image.name == image_name:
                return image
        return None

    def __get_kernel_file_name(self, kernel_url):
        idx = kernel_url.rfind("/")
        if idx == -1:
            return False, None
        idx2 = kernel_url.rfind(".bz2")
        if idx2 != -1:
            path = kernel_url[idx+1:idx2]
            compressed = True
        else:
            path = kernel_url[idx+1:]
            compressed = False
        return compressed, path

    def __download_kernel(self, kernel_url):
        """ Download and uncompress the UML kernel configured in the
            .cassilda profile """
        # get the kernel file name from the url
        compressed, path = self.__get_kernel_file_name(kernel_url)
        if path == None:
            raise ValueError("Malformed URL")
        print("Retrieving kernel from ", kernel_url)
        f = urllib.urlopen(kernel_url)
        # Read the entire file into a binary buffer
        bin = f.read()
        f.close()

        # If it was a bzip2 archive, decompress
        # it directly on the buffer (and remove
        # the bz2 extension from the destination
        # path
        if compressed:
            print("Uncompressing file into ", path)
            debin = bz2.decompress(bin)
            bin = debin
        # Write the file
        print("Writing the file into ", path)
        t = open(path, 'wb')
        t.write(bin)
        t.close

    def run(self, imagename, termnum=0):
        """ Setup firewall rules and call runner object to run the image """
        if not os.geteuid() == 0:
            raise Exception("Only root can run this (yet)")
        image = self[imagename]
        if image == None:
            raise ValueError("No image with name " + imagename + " found")

        c, kernelpath = self.__get_kernel_file_name(self.kernelurl)

        if not os.path.exists(kernelpath):
            self.__download_kernel(self.kernelurl)
        os.chmod(kernelpath, 0o755)
        runner = Runner(image.imagename, UML, self.networks,
            imagename, kernelpath, memory = image.memory)
        for net in self.networks.get_networks_by_host(image.name):
            self.firewall.set_iface(net.name, image.name)
        try:
            runner.run(termnum)
            # time.sleep(20)
        except:
            for net in self.networks.get_networks_by_host(image.name):
                self.firewall.unset_iface(net.name, image.name)
            raise
        image.runner = runner

    def interact(self, imagename):
        if not self.running(imagename):
            print 'Image is not running, nowhere to attach to'
        else:
            image = self[imagename]
            image.runner.interact()
 
    def running(self, imagename):
        image = self[imagename]
        return image.runner.running()

    def run_all(self):
        t = 0
        """ Run all images in the .cas """
        for i in self.images:
            self.run(i.name, termnum=t)
            t += 1

    def finish(self, imagename):
        """ unset firewall rules after image ends (to be done automatically
            when known how) """
        for net in self.networks.get_networks_by_host(imagename):
            self.firewall.unset_iface(net.name, imagename)

    def finish_all(self):
        """ Run all images in the .cas """
        for i in self.images:
            self.finish(i.name)

def main():
    try:
        u = Cassilda(sys.argv[1])
    except IndexError:
        print("cassilda needs exactly 1 parameter")
        exit(1)
    if not u.install_and_configure("all"):
        exit(1)
    exit(0)

if __name__ == "__main__":
    main()

