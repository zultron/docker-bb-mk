#								-*-python-*-
# Set up docker-bb configuration
import os, sys, time
topdir = os.path.realpath(os.path.join(
        os.path.dirname(__file__), '..'))
pythondir = os.path.join(topdir, 'lib', 'python')
sys.path.append(pythondir)

from dbb.config import config as Config
config = Config(os.path.join(topdir, "config.yaml"))

# If container is not buildmaster, pretend to be a daemon
while True:
    time.sleep(10)

import os

from twisted.application import service
from buildbot.master import BuildMaster

rotateLength = 10000000
maxRotatedFiles = 10
configfile = os.path.join(config.base_dir, 'master.cfg')

# Default umask for server
umask = None

# note: this line is matched against to check that this is a buildmaster
# directory; do not edit it.
application = service.Application('buildmaster')
from twisted.python.logfile import LogFile
from twisted.python.log import ILogObserver, FileLogObserver
logfile = LogFile.fromFullPath(os.path.join(config.master_dir, "twistd.log"),
                               rotateLength=rotateLength,
                               maxRotatedFiles=maxRotatedFiles)
application.setComponent(ILogObserver, FileLogObserver(logfile).emit)

m = BuildMaster(config.master_dir, configfile, umask)
m.setServiceParent(application)
m.log_rotation.rotateLength = rotateLength
m.log_rotation.maxRotatedFiles = maxRotatedFiles
