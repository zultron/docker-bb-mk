# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Portions Copyright Buildbot Team Members

from __future__ import with_statement
# Portions Copyright Canonical Ltd. 2009

"""A LatentSlave that uses DigitalOcean to instantiate the slaves on demand.
"""

import os
import re
import time

import digitalocean

from twisted.internet import defer
from twisted.internet import threads
from twisted.python import log

from buildbot import interfaces
from buildbot.buildslave.base import AbstractLatentBuildSlave

class DigitalOceanLatentBuildSlave(AbstractLatentBuildSlave):

    _poll_resolution = 5

    def __init__(self, name, password, droplet_name, token, region, image,
                 size_slug, backups=False,
                 max_builds=None, notify_on_missing=[], missing_timeout=60 * 20,
                 build_wait_timeout=60 * 10, properties={}, locks=None):

        build_wait_timeout = 60*10 # FIXME:  Wait for Docker to start?
        AbstractLatentBuildSlave.__init__(
            self, name, password, max_builds, notify_on_missing,
            missing_timeout, build_wait_timeout, properties, locks)

        self.token = token
        self.name = name
        self.region=region
        self.image=image
        self.size_slug=size_slug
        self.backups=backups

        self.mgr = digitalocean.Manager(token=token)

    def _image_id(self):
        return ([ i.id for i in self.mgr.get_my_images()
                  if i.name == self.image ] + [None])[0]

    def start_instance(self, build):
        if self.droplet is not None:
            raise ValueError('instance active')
        return threads.deferToThread(self._create)

    def _create(self):
        droplet = digitalocean.Droplet(
            token=self.token,
            name=self.name,
            region=self.region,
            image=self._image_id(),
            size_slug=self.size_slug,
            backups=self.backups,
        )
        log.msg("Creating slave %s in droplet %s:  "
                "region=%s; image=%s; size=%s" %
                (self.slavename, self.name, self.region,
                 self._image_id(), self.size_slug))
        droplet.create()
        self._wait_for_droplet()

        if self.droplet is None:
            log.msg('%s %s failed to start droplet %s' %
                    (self.__class__.__name__, self.slavename, self.name))
            raise interfaces.LatentBuildSlaveFailedToSubstantiate(
                self.name, 'non-existent')

        return [self.name, self.droplet.id, self.droplet.created_at]

    def _wait_for_droplet(self):
        log.msg('%s %s waiting for droplet %s to start' %
                (self.__class__.__name__, self.slavename, self.name))
        duration = 0
        droplet = self.droplet
        while droplet is None or droplet.status != 'active':
            time.sleep(self._poll_resolution)
            droplet = self.droplet
            duration += self._poll_resolution
            if droplet is None:
                state = 'non-existent'
            else:
                state = droplet.status
            log.msg('%s %s has waited %d minutes for droplet %s (current: %s)' %
                    (self.__class__.__name__, self.slavename, duration // 60,
                     self.name, state))
        log.msg('%s %s droplet %s started on %s '
                'in about %d seconds' %
                (self.__class__.__name__, self.slavename,
                 self.name, droplet.ip_address, duration))

    @property
    def droplet(self):
        return ([ d for d in self.mgr.get_all_droplets() \
                  if d.name == self.name ] + [None])[0]

    def stop_instance(self, fast=False):
        if self.droplet is None:
            # be gentle.  Something may just be trying to alert us that an
            # instance never attached, and it's because, somehow, we never
            # started.
            log.msg("stop_instance():  Droplet %s already stopped?  " \
                    "Doing nothing" % self.name)
            return defer.succeed(None)
        return threads.deferToThread(
            self._destroy_droplet, fast)

    def _destroy_droplet(self, fast=False):
        droplet = self.droplet
        if droplet is None:
            return
        log.msg('stop_instance(): Deleting droplet "%s"' % self.name)
        droplet.destroy()
        duration = 0
        while self.droplet is not None:
            time.sleep(self._poll_resolution)
            duration += self._poll_resolution
            if duration % 60 == 0:
                log.msg(
                    '%s %s has waited %d minutes for droplet %s to end' %
                    (self.__class__.__name__, self.slavename, duration // 60,
                     self.name))
        log.msg('%s %s droplet %s deleted '
                'after about %d minutes %d seconds' %
                (self.__class__.__name__, self.slavename,
                 self.name, duration // 60, duration % 60))
