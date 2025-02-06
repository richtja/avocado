# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: IBM 2008-2009
# Copyright: Red Hat Inc. 2009-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>
# Author: Higor Vieira Alves <halves@br.ibm.com>
# Author: Ramon de Carvalho Valle <rcvalle@br.ibm.com>

#
# This code was adapted from the autotest project,
# client/shared/software_manager.py

import logging

from avocado.utils import process

log = logging.getLogger("avocado.utils.software_manager")


class BaseBackend:
    """
    This class implements all common methods among backends.
    """

    def install_what_provides(self, path):
        """
        Installs package that provides [path].

        :param path: Path to file.
        """
        provides = self.provides(path)  # pylint: disable=E1101
        if provides is not None:
            return self.install(provides)  # pylint: disable=E1101
        log.warning("No package seems to provide %s", path)
        return False

    @staticmethod
    def _run_cmd(cmd):
        """
        Helper for running a backend command.

        :param cmd: Command to run.
        """
        try:
            process.system(cmd, sudo=True)
            return True
        except process.CmdError as details:
            log.error("Failed to run command: %s", details)
            return False
