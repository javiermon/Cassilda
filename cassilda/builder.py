__version__ = "cassilda 0.0.1"

"""
Builder class module
"""
import subprocess
import os
import tempfile
import shutil
import time

def print_line(line):
    '''Default Builder callback to print a line'''
    print(line)

class Builder:
    ''' An image builder
        This class defines methods that are used by inheritors to implement
        the builder itself
    '''             
    def __init__(self, log_callback = None):
        ''' Builder constructor, receiving a callback to receive
        lines printed by this module
        '''
        self.distribution = None
        self.mountdir = None
        self.install_string = b''
        if log_callback == None:
            self.log_callback = print_line

    def log(self, line):
        self.log_callback(line)

    def call(self, arguments):
        '''Call subprocess storing it's output in self.install_string'''
        self.install_string += b'\n Builder.call(): ' 
        for a in arguments:
            self.install_string += b' ' + a.encode()
        self.install_string += b'\n'

        process = subprocess.Popen(arguments, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = arguments[0]
            raise subprocess.CalledProcessError(retcode, cmd)

        self.install_string += output

    def install_image(self, packages):
        ''' To be implemented only by inheritors '''
        raise NotImplementedError()

    def install(self, packages, basename, imagename, repository):
        ''' Install wrapper that search in the cache before calling (or not)
        the install_image of the builder '''
        if not os.path.exists(basename):
            return self.install_image(packages, imagename, repository)
            # Copy the image to the basename 
            # self.log("Copying " + imagename + " to " + basename +
            #                                   " after first install") 
            # self.call(["cp", "--sparse=always", imagename, basename])
        else:
            self.log("Copying " + basename + " to " + imagename +
                                            " (not first install)") 
            self.call(["cp", "--sparse=always", basename, imagename])
            return True

    def create_image(self, imagepath, imagesize):
        try:
            f = open(imagepath, 'wb')
            f.seek(imagesize - 1)
            f.write(b'\x00')
            f.close()
            return True
        except:
            raise
            return False

    def make_filesystem(self, imagepath):
        try:
            self.log("Making filesystem... in " + imagepath)
            self.call(["mke2fs", "-q", "-F", imagepath])
            return True
#       except CalledProcessError as (returncode, output):
#           print("Error making filesystem, mkfs returned ", returncode)
#           return False
        except:
            raise
            self.log("Unknown error making filesystem")
            return False

    def mount_filesystem(self, imagepath):
        self.mountdir = tempfile.mkdtemp()
        try:
            self.call(["mount", "-o", "loop", imagepath, self.mountdir])
        except:
            raise
        if not os.path.ismount(self.mountdir):
            return False
        return True

    def umount_filesystem(self):
        try:
            self.call(["umount", self.mountdir])
        except subprocess.CalledProcessError:
            self.system("for i in $(lsof | grep " + self.mountdir +
                " | awk '{ print $2 }' | sort | uniq); do " +
                " kill $i; done")
            time.sleep(3)
            try:
                self.call(["umount", self.mountdir])
            except:
                raise
        except:
            raise
        if os.path.ismount(self.mountdir):
            return False
        os.rmdir(self.mountdir)
        self.mountdir = None
        return True

    def create_dir(self, path):
        os.makedirs(self.mountdir + path)
        return True

    def append_to_file(self, path, line, overwrite=False):
        p = self.mountdir + path
        if os.path.exists(p) and not overwrite:
            f = open(p, 'a')
        else:
            f = open(p, 'w')
        f.write(line)
        f.close()

    def replace_in_file(self, path, pattern, replacement):
        p = self.mountdir + path
        if not os.path.exists(p):
            raise Exception('builder.replace_in_file:' +
                'requested path ' + path + ' does not exist')
        t = tempfile.NamedTemporaryFile(delete=False)
        f = open(p, 'r')
        for s in f:
            i = s.find(pattern)
            if i != -1:
                s = s.replace(pattern, replacement)
            t.write(s)
        tname = t.name
        t.close()
        f.close()
        shutil.copyfile(tname, p)
        os.remove(tname)

    def mount_sys_and_dev(self):
        try:
            self.log("Mounting sys...")
            self.call(["mount", "-o", "bind", "/sys/",
                            self.mountdir + "/sys/"])
        except:
            return False
        try:
            self.log("Mounting proc...")
            self.call(["mount", "-o", "bind", "/proc/",
                            self.mountdir + "/proc/"])
        except:
            self.call(["umount", self.mountdir + "/proc/"])
            return False
        return True

    def umount_sys_and_dev(self):
        try:
            self.log("Umounting sys and proc")
            self.call(["umount", self.mountdir + "/sys/"])
            self.call(["umount", self.mountdir + "/proc/"])
        except:
            return False
        return True

    def chmod(self, path, mode):
        ''' chmod a file into the image (mount first) '''
        os.chmod(self.mountdir + path, mode)

    def system(self, command):
        p = subprocess.Popen(command, shell=True)
        sts = os.waitpid(p.pid, 0)[1]

    def build(self, image, repository, size):
        r = self.build_image(image, repository, size)
        if r == False:
           return None 
        return self

"""
    @staticmethod
    def build(image, repository, **kargs):
        mybuilder = BuilderFactory.newBuilder(image.distribution,**kargs)
        mybuilder.build_image(image, repository)
        return mybuilder

class BuilderFactory(object):
    @staticmethod
    def newBuilder(buildertype, **kargs):
        try:
            for builderclass in Builder.__subclasses__():
                if buildertype == builderclass.buildertype:
                    return builderclass(**kargs)
        except:
            raise ValueError('No matching builder "%s".' % buildertype)

"""

