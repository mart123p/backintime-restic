# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import configfile


class ProgressFile(configfile.ConfigFile):

    RSYNC = 50  # Legacy constant kept for backward compatibility
    RESTIC = 60  # Progress file constant for restic

    def __init__(self, cfg, filename=None):
        super(ProgressFile, self).__init__()
        self.config = cfg
        self.filename = filename

        if self.filename is None:
            self.filename = self.config.takeSnapshotProgressFile()

    def save(self):
        return super(ProgressFile, self).save(self.filename)

    def load(self):
        return super(ProgressFile, self).load(self.filename)

    def fileReadable(self):
        return os.access(self.filename, os.R_OK)
