# See http://docker-py.readthedocs.org/en/latest/api/

import docker
import dockerpty
from dbb.docker_context import docker_context
from dbb.init import init
import sys, os, re, socket

class container(object):
    def __init__(self, config):
        self.config = config
        self.context = docker_context(config)
        self._init = init(config)

    @property
    def c(self):
        """Docker client object, generated only on demand"""
        if not hasattr(self, '_c'):
            self._c = docker.Client(base_url='unix://var/run/docker.sock',
                                    version='auto')
        return self._c

    re_subs = (
        # Undo docker-py markup, {"stream":"[...]"}
        (r'^{\"stream\":\"(.*)\"}\s*$', lambda m: m.group(1)),
        # Escaped characters
        (r'\\u0026', '&'),
        (r'\\(u0009|t)', ' '), # tab -> spc
        (r'\\u003c', '<'),
        (r'\\u003e', '>'),
        (r'\\u001b\[[0-9]+m', ''), # Terminal colors
        # Whitespace
        (r'\\r', '\r'), # LF
        (r'\\n', '\n'), # CR
        (r' +', ' '), # collapse spaces
        )

    def image(self):
        ilist = [ i for i in self.c.images()
                  if u'%s:latest' % self.config.hostname in i['RepoTags'] ]
        return (ilist + [None])[0]

    def build(self):
        output = self.c.build(
            fileobj = self.context.file(),
            custom_context = True, # indicate fileobj is a tarball
            tag = self.config.hostname,
            rm = True,
            )

        for line in output:
            # Make output readable
            for regex, repl in self.re_subs:
                line = re.sub(regex, repl, line)
            sys.stdout.write(line)
        sys.stderr.write("Built image, tags %s\n" % \
                             ', '.join(self.image()['RepoTags']))

    def container(self):
        clist = [ c for c in self.c.containers(all=True)
                  if u'/%s' % self.config.hostname in c['Names'] ]
        return (clist + [None])[0]

    def create_container(self, cmd=None):
        if cmd is None:
            cmd = ["/usr/bin/sudo", "-n", \
                   "/usr/bin/supervisord", "-n", \
                   "-c", "/etc/supervisor/supervisord.conf"]
        c = self.c.create_container(
            image = self.config.hostname,
            detach = False,
            stdin_open = True,
            command = cmd,
            hostname = self.config.hostname,
            name = self.config.hostname,
            user = self.config.uid,
            tty = True,
            ports = [8010, 9989, 22],
            environment = dict(
                DISPLAY = os.environ.get('DISPLAY',''),
                HOSTNAME = socket.gethostname(),
                ),
            volumes = [self.config .container_dir, '/tmp/.X11-unix'],
            host_config = self.c.create_host_config(
                binds = {
                    self.config.base_dir : dict(
                        bind = self.config.container_dir,
                        mode = 'rw',
                        ),
                    '/tmp/.X11-unix' : dict( # X display
                        bind = '/tmp/.X11-unix',
                        mode = 'rw',
                        ),
                    },
                port_bindings = {
                    8010 : 80,
                    9989 : 9989,
                    22 : 2222,
                    },
                privileged = True,
                )
            )
        print "Created container %s" % c['Id'][:12]

    def is_running(self):
        if not self.container():
            return False
        i = self.c.inspect_container(self.config.hostname)
        return i['State']['Running']

    def run(self, cmd=None):
        if self.container() and self.is_running():
            sys.stderr.write("Error:  container already running\n")
            sys.exit(1)

        # Create the container if needed
        if not self.container():
            self.create_container(cmd)
        else:
            sys.stderr.write("Warning:  container already created\n")

        # Start the container if needed
        self.c.start(self.config.hostname)
        sys.stderr.write("Container started\n")

    def logs(self):
        if not self.container() or not self.is_running():
            return
        for l in self.c.logs(self.config.hostname, stream=True):
            sys.stdout.write(l)

    def init(self):
        if os.environ.get('CONTAINER', None) == 'docker-bb':
            # Assume we're in the container; initialize it
            self._init.init()
        else:
            # Assume we're in the host OS; re-run command in container
            if self.container():
                sys.stderr.write(
                    "Error:  container exists; please remove before init\n")
                sys.exit(1)
            try:
                cmd = [self.config.dbb_executable,
                          "-H", self.config.hostname, "--init"]
                sys.stderr.write("Re-running in Docker container\n")
                self.run(cmd)
                self.logs()
            except Exception as e:
                sys.stderr.write("Exception:  %s\n" % e)
            finally:
                self.remove()

    def attach(self):
        if not self.container():
            sys.stderr.write("Error:  container does not exist\n")
            sys.exit(1)

        dockerpty.start(
            self.c,
            self.c.inspect_container(self.config.hostname))

    def stop(self):
        if not self.is_running():
            sys.stderr.write("Error:  container is not running\n")
            sys.exit(1)
        self.c.stop(self.config.hostname)
        sys.stderr.write("Container stopped\n")

    def remove(self):
        if not self.container():
            sys.stderr.write("Error:  container does not exist\n")
            sys.exit(1)

        if self.is_running():
            sys.stderr.write("Error:  stop container before removing\n")
            sys.exit(1)

        self.c.remove_container(self.config.hostname)
        sys.stderr.write("Container removed\n")

    def dump(self):
        from pprint import pprint

        # Print Docker info
        print "Docker:"
        pprint(self.c.info())

        # Print container info
        print "Container:"
        if self.container():
            pprint(self.c.inspect_container(self.config.hostname))
        else:
            print "    (none)"
        
        # Print image info
        print "Image:"
        if self.image():
            pprint(self.c.inspect_image(self.config.hostname))
        else:
            print "    (none)"
