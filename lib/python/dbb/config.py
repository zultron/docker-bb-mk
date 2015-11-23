import socket, yaml, os, subprocess

class slave_config(object):
    def __init__(self, config, slave_name):
        self.global_config = config
        self.select(slave_name)

    def select(self, slave_name):
        """Select a new default slave"""
        self.name = slave_name
        self.config = self.global_config.config['slaves'][self.name]
        return self

    def get(self, slave_name):
        """Generator:  get slave object by name"""
        return slave_config(self.global_config, slave_name)

    @property
    def base_image(self):
        return self.config.get('base_image','debian:jessie')

    @property
    def tcl_ver(self):
        return self.config.get('tcl_ver','8.6')

    @property
    def flavors(self):
        return self.config.get('flavors',['posix'])

    @property
    def parallel_jobs(self):
        return self.config.get('parallel_jobs',1)

    @property
    def master(self):
        """Master for this slave"""
        return self.config['master']

    @property
    def password(self):
        """Password for this slave"""
        return self.config['password']

    @property
    def dir(self):
        return os.path.join(self.global_config.base_dir, "slave")


    def slave_list(self, master=None):
        """
        Return list of slave names for a master
        """
        return [ s for s in self.global_config.config['slaves']
                 if self.global_config.config['slaves'][s]['master'] == \
                     (master or self.global_config.hostname) ]


class config(object):
    def __init__(self, config_file, hostname=None):
        self.hostname = hostname or os.environ.get('CONTAINER', None)
        if self.hostname is None:
            raise RuntimeError("Please specify hostname to configure")
        self.config_file = config_file
        self.config = yaml.load(file(config_file,"r"))
        self.slave = slave_config(self, self.hostname)

    def dump(self):
        from pprint import pprint
        pprint(self.config)

    @property
    def container_dir(self):
        """Configured mount destination for this tree in Docker filesystem"""
        return self.config.get('container_dir', '/home/docker/bb')

    @property
    def base_dir(self):
        """Base directory of this tree"""
        return os.path.dirname(os.path.realpath(self.config_file))

    @property
    def dbb_executable(self):
        return "bin/dbb"  # lame, I know; needs to work both inside and out

    @property
    def lib_dir(self):
        """Lib directory within this tree"""
        return os.path.join(self.base_dir, "lib")

    @property
    def debian_mirror(self):
        return self.config.get('debian_mirror', 'httpredir.debian.org')

    @property
    def http_proxy(self):
        return self.config.get('http_proxy', '')

    @property
    def uid(self):
        return self.config.get('uid', os.getuid())

    @property
    def gid(self):
        return self.config.get('gid', os.getgid())

    @property
    def maintainer_name(self):
        return self.config.get('maintainer_name', 'John Doe')

    @property
    def maintainer_email(self):
        return self.config.get('maintainer_email', 'jdoe@example.com')

    @property
    def maintainer_keys(self):
        return self.config.get('maintainer_keys', [])

    @property
    def supervisord_conf(self):
        return os.path.join("%s/lib/supervisord.conf.d" % self.container_dir)

    @property
    def subs(self):
        """
        Return list of substitutions used in templates for Docker
        image build
        """
        return dict(
            hostname = self.hostname,
            base_dir = self.base_dir,
            container_dir = self.container_dir,
            lib_dir = self.lib_dir,
            debian_mirror = self.debian_mirror,
            http_proxy = self.http_proxy,
            uid = self.uid,
            gid = self.gid,
            base_image = self.slave.base_image,
            tcl_ver = self.slave.tcl_ver,
            maintainer_name = self.maintainer_name,
            maintainer_email = self.maintainer_email,
            supervisord_conf = self.supervisord_conf,
            master_dir = self.master_dir,
            slave_dir = self.slave.dir,
            )

    def render_template(self, fname, extra_subs = {}):
        res = ''
        subs = self.subs.copy()
        subs.update(extra_subs)
        with open(fname, 'r') as f:
            for line in f:
                res += line % subs
        return res


    ##########################
    # Buildbot configuration

    @property
    def web_title(self):
        return self.config.get('web_title', '(unknown)')

    @property
    def web_titleURL(self):
        return self.config.get('web_titleURL', 'http://localhost:8010')

    @property
    def buildbotURL(self):
        return self.config.get('buildbotURL', 'http://localhost:8010')

    @property
    def git_repo(self):
        return self.config['git_repo']

    @property
    def git_branch(self):
        return self.config.get('git_branch', 'master')

    @property
    def admin_users(self):
        return self.config.get('admin_users', {})

    @property
    def master_dir(self):
        return os.path.join(self.base_dir, "master")

    @property
    def slave_list(self):
        return self.slave.slave_list()
