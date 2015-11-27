import socket, yaml, os, subprocess

class AbstractSlaveConfig(object):
    global_config = None
    type_map = {}
    slave_class_name = None

    class __metaclass__(type):
        __child_classes__ = []

        def __new__(meta, name, bases, dct):
            cls = type.__new__(meta, name, bases, dct)
            meta.__child_classes__.append(cls)
            return cls

    def __init__(self, slave_name=None):
        if slave_name is None:
            slave_name = self.get_slave_name_by_host()
        self.name = slave_name
        self.config = self.slave_dict[self.name]

    @classmethod
    def get_slave_config(cls, slave_name=None):
        if slave_name is None:
            slave_name = cls.get_slave_name_by_host()
        slave_params = cls.global_config.config['slaves'][slave_name]
        slave_type = slave_params.get('slave_type', 'vanilla')
        slave_config_cls = ([ c for c in cls.__child_classes__ \
                              if c.slave_class_name == slave_type ] \
                            + [None])[0]
        if slave_config_cls is None:
            raise RuntimeError('Unable to find slave class for "%s"' %
                               slave_type)
        return slave_config_cls(slave_name)

    @classmethod
    def get_slave_name_by_host(cls):
        h = socket.gethostname()
        for (name, params) in cls.global_config.config['slaves'].items():
            if params['host'] == h:
                return name
        raise RuntimeError('Unable to find slave from hostname "%s"' % h)

    @property
    def slave_dict(self):
        return self.global_config.config.get('slaves',{})

    def builder_slaves(self, builder):
        return [ s for s in self.slave_dict \
                 if self.slave_dict[s].get('builders', None) == builder ]

    @property
    def host(self):
        return self.config.get('host', self.name)

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
    def password(self):
        """Password for this slave"""
        return self.config['password']

    @property
    def dir(self):
        return os.path.join(self.global_config.base_dir, "slave")

    def build_slave_object(self):
        from buildbot import buildslave
        return buildslave.BuildSlave(self.name, self.password)

    def dump(self):
        from pprint import pprint
        pprint(self.__dict__)

class SlaveConfig(AbstractSlaveConfig):
    slave_class_name = 'vanilla'

class DigitalOceanSlaveConfig(AbstractSlaveConfig):
    slave_class_name = 'DigitalOcean'

    def __init__(self, slave_name):
        super(DigitalOceanSlaveConfig, self).__init__(slave_name)
        self.image = self.config['image']
        self.size_slug = self.config['size_slug']
        self.region = self.config['region']
        self.token = self.global_config.config['digitalocean']['token']

    def build_slave_object(self):
        from digitalocean_buildslave import DigitalOceanLatentBuildSlave
        return DigitalOceanLatentBuildSlave(
            name=self.name,
            password=self.password,
            droplet_name=self.name,
            token=self.token,
            region=self.region,
            image=self.image,
            size_slug=self.size_slug,
        )


class config(object):
    def __init__(self, config_file, hostname=None):
        self.config_file = config_file
        self.config = yaml.load(file(config_file,"r"))
        AbstractSlaveConfig.global_config = self

        # Go through some antics to automatically figure out hostname
        host_hostname = socket.gethostname()
        if hostname is None:  # Look in slaves list
            host_slaves = [
                s for s in self.config['slaves'] \
                if self.config['slaves'][s]['host'] == socket.gethostname() ]
            if len(host_slaves) == 1:
                hostname = host_slaves[0]
        self.hostname = hostname

        self.slave = AbstractSlaveConfig.get_slave_config(hostname)

    def dump(self):
        from pprint import pprint
        pprint(self.config)
        self.slave.dump()

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
    def host(self):
        """Docker host name"""
        return os.environ.get('HOSTNAME', None) or socket.gethostname()

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
            master_name = self.master_name,
            master_host = self.master_host,
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
    def master_name(self):
        return self.config['master_name']

    @property
    def master_host(self):
        return self.config['master_host']

    @property
    def master_dir(self):
        return os.path.join(self.base_dir, "master")

    @property
    def slaves(self):
        """
        Return list of slave names
        """
        return self.config.get('slaves',{}).keys()

    def get_slave_config(self, slave_name):
        return AbstractSlaveConfig.get_slave_config(slave_name)

