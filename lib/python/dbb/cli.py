import argparse, os
from dbb.config import config
from dbb.container import container
from dbb.setup import setup

class cli(object):
    def __init__(self, topdir):
        self.parse()
        if not os.path.exists(self.args.config_file):
            c = os.path.join(topdir, self.args.config_file)
            if os.path.exists(c):
                self.args.config_file = c
            #else: throw a suitable error
        self.config = config(self.args.config_file, self.args.docker_hostname)

    def parse(self):
        self.parser = argparse.ArgumentParser(
            description='Manage Buildbot in Docker')
        cmdgroup = self.parser.add_mutually_exclusive_group(
            required=True)
        # configuration args
        self.parser.add_argument("--docker-hostname", "-H",
                                 help="Container host name")
        self.parser.add_argument("--config-file", "-c",
                                 default="config.yaml",
                                 help="YAML configuration file")
        # main operations
        cmdgroup.add_argument("--build", action="store_true",
                              help="Build container")
        cmdgroup.add_argument("--run", action="store_true",
                              help="Run container")
        cmdgroup.add_argument("--attach", action="store_true",
                              help="Attach container")
        cmdgroup.add_argument("--stop", action="store_true",
                              help="Stop container")
        cmdgroup.add_argument("--remove", action="store_true",
                              help="Remove container (must be stopped)")
        cmdgroup.add_argument("--setup", action="store_true",
                              help="(Internal use) Container startup routines")
        # debug
        cmdgroup.add_argument("--dump-config", action="store_true",
                              help="Dump configuration")
        cmdgroup.add_argument("--dump-dockerfile", action="store_true",
                              help="Dump Dockerfile")
        cmdgroup.add_argument("--dump-deb-control", action="store_true",
                              help="Dump Debian control file")
        cmdgroup.add_argument("--dump-context", action="store_true",
                              help="Dump Docker context as tarball")
        cmdgroup.add_argument("--dump-container", action="store_true",
                              help="Dump container info")

        self.args = self.parser.parse_args()

    def doit(self):
        # main operations
        if self.args.build:
            self.docker.build()
        if self.args.run:
            self.docker.run()
        if self.args.attach:
            self.docker.attach()
        if self.args.stop:
            self.docker.stop()
        if self.args.remove:
            self.docker.remove()
        if self.args.setup:
            setup(self.config)
        # debug
        if self.args.dump_config:
            self.config.dump()
        if self.args.dump_dockerfile:
            self.docker.context.dockerfile.dump()
        if self.args.dump_deb_control:
            self.docker.context.deb_control.dump()
        if self.args.dump_context:
            self.docker.context.dump()
        if self.args.dump_container:
            self.docker.dump()

    @property
    def docker(self):
        # Instantiate container on demand
        if not hasattr(self, '_docker'):
            self._docker = container(self.config)

        return self._docker
