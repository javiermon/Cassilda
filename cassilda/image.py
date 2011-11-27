__version__ = "cassilda 0.0.1"

"""
Image class module for cassilda framework
"""
import hashlib
import os
from .runner import *

class Image:
    """Represents an installing or running Image"""
    def __init__(self, name, size, memory, distribution, packages):
        self.name = name
        self.size = size
        self.memory = memory
        self.distribution = distribution
        self.packages = packages
        self.basename = self.distribution + ".img"
        self.imagename = self.distribution + "-" + self.name + ".img"
        self.runner = None

    def already_installed(self):
        return os.path.exists(self.imagename)

