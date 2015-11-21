import socket, yaml, os, subprocess

class config(object):
    def __init__(self, config_file, hostname=None):
        self.hostname = hostname or socket.gethostname()
        self.config_file = config_file
        self.config = yaml.load(file(config_file,"r"))

    def dump(self):
        from pprint import pprint
        pprint(self.config)

    @property
    def base_dir(self):
        return os.path.dirname(os.path.realpath(self.config_file))

    @property
    def container_dir(self):
        return self.config.get('container_dir', '/home/docker/bb')

    @property
    def lib_dir(self):
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

    def slave_config(self, slave=None):
        return self.config.get('slaves',{}).get(slave or self.hostname,{})

    @property
    def base_image(self):
        return self.slave_config().get('base_image','debian:jessie')

    @property
    def tcl_ver(self):
        return self.slave_config().get('tcl_ver','8.6')

    def _maintainer(self,what):
        res = self.config.get('maintainer_%s' % what,None)
        if res is None:
            cmd = ["git","config","--get","user.%s" % what]
            with subprocess.Popen(cmd,stdout=subprocess.PIPE).stdout as p:
                res = p.read()[:-1]
        return res

    @property
    def maintainer_name(self):
        return self._maintainer('name')

    @property
    def maintainer_email(self):
        return self._maintainer('email')

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
            base_image = self.base_image,
            tcl_ver = self.tcl_ver,
            maintainer_name = self.maintainer_name,
            maintainer_email = self.maintainer_email,
            supervisord_conf = self.supervisord_conf,
            master_dir = self.master_dir,
            slave_dir = self.slave_dir,
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
    def slave_dir(self):
        return os.path.join(self.base_dir, "slave")

    def slaves(self, master=None):
        """
        Return slice of 'slaves' dict that matches the master
        """
        return [ s for s in self.config['slaves']
                 if self.slave_master(s) == (master or self.hostname) ]

    def slave_master(self, slave=None):
        """
        Return master for this slave
        """
        return self.slave_config(slave)['master']

    def slave_password(self, slave=None):
        """
        Return master for this slave
        """
        return self.slave_config(slave)['password']

    def slave_flavors(self):
        return self.slave_config().get('flavors',['posix'])
