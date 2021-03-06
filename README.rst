========
Cassilda
========
-------------------------------------------------------------
an UML/QEMU/XEN image generator, runner and testing framework
-------------------------------------------------------------

Installation and usage
----------------------
Download
~~~~~~~~
Get last version from github:.

  git clone git://github.com/odkq/Cassilda.git

Requirements
~~~~~~~~~~~~
* Python 2.6+             http://www.python.org
* pyYAML 3.09+            http://www.pyyaml.org
* netaddr 0.7.4+          https://github.com/drkjam/netaddr
* pexpect 2.3+            http://www.noah.org/wiki/pexpect

* uml-utilities 20070815+ http://user-mode-linux.sourceforge.net/downloads.html

To generate debian images:

* debootstrap 1.0.26+     http://wiki.debian.org/Debootstrap

Optional: to speed up reinstalling images, have an apt-proxy such
as apt-cacher-ng installed

To install all dependencies in debian squeeze, do::

  apt-get install python python-yaml python-netaddr python-pexpect \
  uml-utilities debootstrap apt-cacher-ng

Installation
~~~~~~~~~~~~

Cassilda uses the regular distutils setup.py, install with::

  sudo python ./setup.py install

It will put the cassilda python modules wherever your system-wide
python installation needs it, and the documentation/examples in
/usr/share/doc/Cassilda

Usage
~~~~~

Example session::

    Launch the python (or ipython or bpython) interpreter as root
    in a directory with sufficient space to store the generated
    images:

    # cd /tmp    
    # ipython

    >>> import cassilda
    ## Load settings from a YAML cassilda profile
    >>> c = cassilda.Cassilda(
	"/usr/share/doc/Cassilda/examples/apache_mysql.cas")
    ## Install an image
    >>> c.build("apache_server")
    (output from cassilda)
    ## Install all images
    >>> c.build("mysql_server")
    >>> c.build("web_client")
    ## Run an image
    >>> c.run("apache_server")
    ## Interact (with the console) of a running image
    >>> c.interact('apache_server')
    ## Press the regular telnet escape char ^] to return

Cassilda Profile description
----------------------------
To be written yet

Images
~~~~~~
To be written yet

Installers
~~~~~~~~~~
To be written yet

Testing with pexpect
~~~~~~~~~~~~~~~~~~~~
To be written yet

Extending Cassilda
------------------
Writing builders
~~~~~~~~~~~~~~~~
To be written yet

Writing runners
~~~~~~~~~~~~~~~
To be written yet

Writing interfaces
~~~~~~~~~~~~~~~~~~

