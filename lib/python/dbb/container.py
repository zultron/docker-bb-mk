# See http://docker-py.readthedocs.org/en/latest/api/

import docker
import dockerpty
from dbb.docker_context import docker_context
import sys, os, re

class container(object):
    def __init__(self, config):
        self.c = docker.Client(base_url='unix://var/run/docker.sock',
                               version='auto')
        self.config = config
        self.context = docker_context(config)

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

    def create_container(self):
        c = self.c.create_container(
            image = self.config.hostname,
            detach = False,
            stdin_open = True,
            command = ["bash", "-i"],
            hostname = self.config.hostname,
            name = self.config.hostname,
            user = self.config.uid,
            tty = True,
            ports = [8010],
            environment = dict(
                DISPLAY = os.environ['DISPLAY']
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
                    8010 : 8010,
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

    def run(self):
        if self.container() and self.is_running():
            sys.stderr.write("Error:  container already running\n")
            sys.exit(1)

        # Create the container if needed
        if not self.container():
            self.create_container()
        else:
            sys.stderr.write("Warning:  container already created\n")

        # Start the container if needed
        self.c.start(self.config.hostname)
        sys.stderr.write("Container started\n")

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
