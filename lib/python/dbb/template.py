import os
from io import BytesIO

class template(object):
    def __init__(self, config):
        self.config = config

    @property
    def subs(self):
        return {}

    @property
    def template(self):
        return os.path.join(self.config.lib_dir, self.template_name)

    @property
    def file(self):
        return BytesIO(self.__str__().encode('utf-8'))

    def dump(self):
        print self

    def __str__(self):
        return self.config.render_template(self.template, self.subs)
