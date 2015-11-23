# Building the Docker image

## Install dependencies

- docker
  - version deps:  1.0.1 bad, 1.6.2 good
- docker-py, Docker API python wrapper
  - version deps:  0.5.3 bad (Jessie), 1.5.0 good
- dockerpty, like `docker attach`
- pyyaml, for reading config file

All dependencies are already in Scaleway's Docker image.  These
commands install the dependencies for Ubuntu Trusty:

    sudo apt-get install python-pip python-yaml
    sudo apt-get install docker.io
    sudo pip install docker-py
    sudo pip install dockerpty

## Edit configuration

Copy `config.sample.yaml` to `config.sample` and edit, following
inline comments.

For testing, the defaults will mostly work.  The `git_repo` and
`git_branch` must be set.  The `buildbotURL` should be set to the
**external** web interface URL; once this is set, it is difficult to
change, so choose wisely.

## Build Docker image

Build the Docker image, choosing a host name from the config file
`slaves:` section.

    bin/dbb -H d8-64-posix --build

# Initializing and running the Docker container

Initialize the Docker container SSH keys and Build master and slave:

	bin/dbb -H d8-64-posix --init

Create and run the Docker container:

    bin/dbb -H d8-64-posix --run

Attach to the console:

    bin/dbb -H d8-64-posix --attach

Stop and remove the Docker container:

    bin/dbb -H d8-64-posix --stop
    bin/dbb -H d8-64-posix --remove

Set up Buildbot:  (to be written; see `lib/python/dbb/setup.py`)

