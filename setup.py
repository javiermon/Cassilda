#!/usr/bin/env python
from distutils.core import setup

classifiers = [
   "Development Status :: 3 - Alpha",
   "License :: OSI Approved :: GNU General Public License (GPL)",
   "Programming Language :: Python :: 2.6",
   "Topic :: Software Development :: Build Tools",
   "Topic :: Software Development :: Testing",
   "Environment :: Console",
]

setup(
      name = 'Cassilda',
      version = '0.0.1',
      description = "An UML/QEMU/XEN image generator, runner and testing" +
                "framework",
      author = "Pablo Martin and Eduardo Aguilar",
      author_email = "pablo@odkq.com",
      packages = ['cassilda'],
      url = "https://github.com/odkq/Cassilda",
      license = "GPL v3",
      long_description = open('README.rst').read(),
      data_files = [
                    ("/usr/share/doc/Cassilda", 
                            [ "README.rst", "LICENSE"]),
                    ("/usr/share/doc/Cassilda/examples", 
                            ["examples/apache_install.cas",
                            "examples/apache_mysql.cas",
                            "examples/cassilda_install.cas",
                            "examples/mysql_install.cas",
                            "examples/webclient_install.cas",
                            "examples/yodawg.cas" ])
      ],
      classifiers = classifiers
)

