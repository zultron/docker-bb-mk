#								-*-python-*-
# Set up docker-bb configuration
import os, sys
topdir = os.path.realpath(os.path.join(
        os.path.dirname(__file__), '..'))
pythondir = os.path.join(topdir, 'lib', 'python')
sys.path.append(pythondir)

from dbb.config import config as Config
config = Config(os.path.join(topdir, "config.yaml"))

import os

from buildslave.bot import BuildSlave
from twisted.application import service

rotateLength = 10000000
maxRotatedFiles = 10

# note: this line is matched against to check that this is a buildslave
# directory; do not edit it.
application = service.Application('buildslave')

try:
  from twisted.python.logfile import LogFile
  from twisted.python.log import ILogObserver, FileLogObserver
  logfile = LogFile.fromFullPath(os.path.join(config.slave_dir, "twistd.log"),
                                 rotateLength=rotateLength,
                                 maxRotatedFiles=maxRotatedFiles)
  application.setComponent(ILogObserver, FileLogObserver(logfile).emit)
except ImportError:
  # probably not yet twisted 8.2.0 and beyond, can't set log yet
  pass

buildmaster_host = config.slave_master()
port = 9989
slavename = config.hostname
passwd = config.slave_password(slavename)
keepalive = 600
usepty = 0
umask = None
maxdelay = 300
allow_shutdown = None

s = BuildSlave(buildmaster_host, port, slavename, passwd, config.slave_dir,
               keepalive, usepty, umask=umask, maxdelay=maxdelay,
               allow_shutdown=allow_shutdown)
s.setServiceParent(application)

