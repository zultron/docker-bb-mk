def setup(config):
    """
    This is a script called by supervisord on container start.  It
    sets up any run-time configuration.
    """

    setup_ssh_authorized_keys(config)



def setup_ssh_authorized_keys(config):
    import re, os
    with open("/home/docker/.ssh/authorized_keys", 'w') as f:
        for keystr in config.config.get('maintainer_keys',[]):
            f.write(re.sub(r'\n', '', keystr) + "\n")

def setup_buildbot_master(config):
    #buildbot create-master config.master_dir
    pass

def setup_buildbot_slave(config):
    #buildslave create-slave config.slave_dir config.slave_master() config.hostname config.slave_password()
    # echo "config.maintainer_name <config.maintainer_email>" > slave/info/admin
    # echo "config.base_image()"

    pass

