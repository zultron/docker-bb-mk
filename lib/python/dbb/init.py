import os, sys, re, subprocess

class init(object):
    def __init__(self, config):
        self.config = config

    def init(self):
        """Initialize all container run-time configuration."""
        self.ssh_authorized_keys()
        self.buildbot_master()
        self.buildbot_slave()

    def ssh_authorized_keys(self):
        sys.stderr.write("*** Installing SSH authorized_keys\n")
        with open("/home/docker/.ssh/authorized_keys", 'w') as f:
            for keystr in self.config.maintainer_keys:
                f.write(re.sub(r'\n', '', keystr) + "\n")

    def buildbot_master(self):
        if self.config.master_host != self.config.host:
            sys.stderr.write("*** Container is not Buildbot master; not initializing\n")
            return
        cmd = [ "buildbot", "create-master", self.config.master_dir ]
        sys.stderr.write("*** Initializing Buildbot master:  %s\n" % \
                             ' '.join(cmd))
        subprocess.call(cmd)

    def buildbot_slave(self):
        cmd = [ "buildslave", "create-slave", self.config.slave.dir,
                self.config.master_host, self.config.hostname,
                self.config.slave.password ]
        sys.stderr.write("*** Initializing Buildbot slave:  %s\n" % \
                             ' '.join(cmd))
        subprocess.call(cmd)

        admin = "%s <%s>\n" % \
            (self.config.maintainer_name, self.config.maintainer_email)
        host = "%s, from: %s\n" % \
            (self.config.slave.name, self.config.slave.base_image)
        sys.stderr.write("    Admin:  %s    Description:  %s" % (admin, host))

        with open(os.path.join(self.config.slave.dir, 'info/admin'), 'w') as f:
            f.write(admin)
        with open(os.path.join(self.config.slave.dir, 'info/host'), 'w') as f:
            f.write(host)
