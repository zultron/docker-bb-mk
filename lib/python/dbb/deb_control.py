from .template import template

class deb_control(template):
    template_name = 'control.template'
    filename = 'control'

    @property
    def subs(self):
        res = dict(
            xenomai = ''
            )
        if 'xenomai' in self.config.slave.flavors:
            res['xenomai'] = 'xenomai-dev,'
        return res
