import tarfile, sys
from StringIO import StringIO
from io import BytesIO
from dbb.dockerfile import dockerfile
from dbb.deb_control import deb_control

class docker_context(object):
    def __init__(self, config):
        self.config = config
        self.dockerfile = dockerfile(config)
        self.deb_control = deb_control(config)

    def _addfile(self, tarball, template):
        s = template.__str__()
        ti = tarfile.TarInfo(name=template.filename)
        ti.size = len(s)
        ti.uid = self.config.uid
        ti.gid = self.config.gid
        tarball.addfile(ti, StringIO(s))

    def file(self):
        f = BytesIO()
        t = tarfile.TarFile(fileobj=f, mode='w')

        self._addfile(t, self.dockerfile)
        self._addfile(t, self.deb_control)

        t.close()
        f.seek(0)
        return f

    def dump(self):
        with self.file() as f:
            for line in f:
                sys.stdout.write(line)
