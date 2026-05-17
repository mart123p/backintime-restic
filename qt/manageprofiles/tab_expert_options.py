# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2008-2022 Taylor Raak
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""About Expert Options tab"""
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QGridLayout,
                             QLabel,
                             QSpinBox,
                             QLineEdit,
                             QCheckBox)
import tools
from config import Config
import qttools
import messagebox
from manageprofiles.statebindcheckbox import StateBindCheckBox
from bitwidgets import HLineWidget


class ExpertOptionsTab(QDialog):
    """The 'Expert Options' tab in the Manage Profiles dialog."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, parent):  # noqa: PLR0915
        # pylint: disable=too-many-statements
        super().__init__(parent=parent)

        self._parent_dialog = parent

        tab_layout = QVBoxLayout(self)

        # --- initial warning ---
        txt = _(
            'These options are for advanced configurations. Modify '
            'only if fully aware of their implications.'
        )
        label = qttools.create_warning_label(txt)
        tab_layout.addWidget(label)
        tab_layout.addWidget(HLineWidget())

        # --- restic with nice ---
        tab_layout.addWidget(QLabel(
            _("Run 'restic' with '{cmd}':").format(cmd='nice')))

        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)  # left indent
        tab_layout.addLayout(grid)

        self._cb_nice_on_cron = QCheckBox(
            _('as cron job')
            + self._default_string(self.config.DEFAULT_RUN_NICE_FROM_CRON),
            self)
        grid.addWidget(self._cb_nice_on_cron, 0, 1)

        self._cb_nice_on_remote = QCheckBox(
            _('on remote host')
            + self._default_string(self.config.DEFAULT_RUN_NICE_ON_REMOTE),
            self)
        grid.addWidget(self._cb_nice_on_remote, 1, 1)

        # --- restic with ionice ---
        tab_layout.addWidget(QLabel(
            _("Run 'restic' with '{cmd}':").format(cmd='ionice')))
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        tab_layout.addLayout(grid)

        self._cb_ionice_on_cron = QCheckBox(
            _('as cron job')
            + self._default_string(self.config.DEFAULT_RUN_IONICE_FROM_CRON),
            self)
        grid.addWidget(self._cb_ionice_on_cron, 0, 1)

        self._cb_ionice_on_user = QCheckBox(
            _('when taking a manual backup')
            + self._default_string(self.config.DEFAULT_RUN_IONICE_FROM_USER),
            self)
        grid.addWidget(self._cb_ionice_on_user, 1, 1)

        self._cb_ionice_on_remote = QCheckBox(
            _('on remote host')
            + self._default_string(self.config.DEFAULT_RUN_IONICE_ON_REMOTE),
            self)
        grid.addWidget(self._cb_ionice_on_remote, 2, 1)

        # --- restic with nocache ---
        tab_layout.addWidget(QLabel(
            _("Run 'restic' with '{cmd}':").format(cmd='nocache')))

        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        tab_layout.addLayout(grid)

        nocache_available = tools.checkCommand('nocache')
        if not nocache_available:
            grid.addWidget(
                QLabel(
                    '<em>'
                    + _("Please install 'nocache' to enable this option.")
                    + '</em>'),
                0,
                1)

        self._cb_nocache_on_local = QCheckBox(
            _('on local machine')
            + self._default_string(self.config.DEFAULT_RUN_NOCACHE_ON_LOCAL),
            self)
        grid.addWidget(self._cb_nocache_on_local, 1, 1)
        self._cb_nocache_on_local.setEnabled(nocache_available)

        self._cb_nocache_on_remote = QCheckBox(
            _('on remote host')
            + self._default_string(self.config.DEFAULT_RUN_NOCACHE_ON_REMOTE),
            self)
        grid.addWidget(self._cb_nocache_on_remote, 2, 1)

        # --- redirect output ---
        self._cb_redirect_stdout_cron = QCheckBox(
            _('Redirect stdout to /dev/null in cronjobs.')
            + self._default_string(
                self.config.DEFAULT_REDIRECT_STDOUT_IN_CRON),
            self)
        qttools.set_wrapped_tooltip(
            self._cb_redirect_stdout_cron,
            _('Cron will automatically send an email with attached output '
              'of cronjobs if an MTA is installed.')
        )
        tab_layout.addWidget(self._cb_redirect_stdout_cron)

        self._cb_redirect_stderr_cron = QCheckBox(
            _('Redirect stderr to /dev/null in cronjobs.')
            + self._default_string(
                self.config.DEFAULT_REDIRECT_STDERR_IN_CRON),
            self)
        qttools.set_wrapped_tooltip(
            self._cb_redirect_stderr_cron,
            _('Cron will automatically send an email with attached errors '
              'of cronjobs if an MTA is installed.')
        )
        tab_layout.addWidget(self._cb_redirect_stderr_cron)

        # bandwidth limit
        hlayout = QHBoxLayout()
        tab_layout.addLayout(hlayout)

        self._spb_bwlimit = QSpinBox(self)
        self._spb_bwlimit.setSuffix(' ' + _('KB/sec'))
        self._spb_bwlimit.setSingleStep(100)
        self._spb_bwlimit.setRange(0, 1000000)

        self._cb_bwlimit = StateBindCheckBox(
            _('Limit bandwidth usage:'), self, self._spb_bwlimit)
        hlayout.addWidget(self._cb_bwlimit)
        hlayout.addWidget(self._spb_bwlimit)
        hlayout.addStretch()

        qttools.set_wrapped_tooltip(
            self._cb_bwlimit,
            [
                "Uses restic's '--limit-upload' and '--limit-download'.",
                'This option allows you to specify the maximum transfer rate '
                'for the data sent over the network, specified in KiB/sec.',
                '',
                'A value of zero specifies no limit.'
            ]
        )

        self._cb_preserve_acl = QCheckBox(_('Preserve ACL'), self)
        qttools.set_wrapped_tooltip(
            self._cb_preserve_acl,
            [
                'Restic preserves ACLs natively when backing up files.',
                'Enable this to explicitly verify ACL preservation during '
                'backup and restore operations.'
            ]
        )
        tab_layout.addWidget(self._cb_preserve_acl)

        self._cb_preserve_xattr = QCheckBox(
            _('Preserve extended attributes (xattr)'), self)
        qttools.set_wrapped_tooltip(
            self._cb_preserve_xattr,
            [
                'Restic preserves extended attributes natively.',
                'Enable this to explicitly verify xattr preservation during '
                'backup and restore operations.'
            ]
        )
        tab_layout.addWidget(self._cb_preserve_xattr)

        # one file system option
        self._cb_one_filesystem = QCheckBox(
            _('Restrict to one file system'), self)
        qttools.set_wrapped_tooltip(
            self._cb_one_filesystem,
            [
                "Uses restic's '--one-file-system' flag.",
                'This tells restic to avoid crossing filesystem boundaries '
                'when recursing through directories.'
            ]
        )
        tab_layout.addWidget(self._cb_one_filesystem)

        # additional restic options
        tooltip = _('Additional command-line options to pass to restic.')

        self._txt_restic_options = QLineEdit(self)
        self._txt_restic_options.setToolTip(tooltip)

        self._cb_restic_options = StateBindCheckBox(
            _('Pass additional options to restic'),
            self,
            self._txt_restic_options)

        self._cb_restic_options.setToolTip(tooltip)

        sub_grid = QGridLayout()
        sub_grid.addWidget(self._cb_restic_options, 0, 0)
        sub_grid.addWidget(self._txt_restic_options, 0, 1)
        tab_layout.addLayout(sub_grid)

        tab_layout.addStretch()

    @property
    def config(self) -> Config:
        """The config instance."""
        return self._parent_dialog.config

    def _default_string(self, value: bool) -> str:
        return ' ' + _('(default: {})').format(
            _('enabled') if value else _('disabled'))

    def load_values(self):
        """Load config values into the GUI"""

        self._cb_nice_on_cron.setChecked(self.config.niceOnCron())
        self._cb_ionice_on_cron.setChecked(self.config.ioniceOnCron())
        self._cb_ionice_on_user.setChecked(self.config.ioniceOnUser())
        self._cb_nice_on_remote.setChecked(self.config.niceOnRemote())
        self._cb_ionice_on_remote.setChecked(self.config.ioniceOnRemote())
        self._cb_nocache_on_local.setChecked(
            self.config.nocacheOnLocal()
            and self._cb_nocache_on_local.isEnabled())
        self._cb_nocache_on_remote.setChecked(self.config.nocacheOnRemote())
        self._cb_redirect_stdout_cron.setChecked(
            self.config.redirectStdoutInCron())
        self._cb_redirect_stderr_cron.setChecked(
            self.config.redirectStderrInCron())
        self._cb_bwlimit.setChecked(self.config.bwlimitEnabled())
        self._spb_bwlimit.setValue(self.config.bwlimit())
        self._cb_preserve_acl.setChecked(self.config.preserveAcl())
        self._cb_preserve_xattr.setChecked(self.config.preserveXattr())

        self._cb_one_filesystem.setChecked(self.config.oneFileSystem())
        self._cb_restic_options.setChecked(self.config.rsyncOptionsEnabled())
        self._txt_restic_options.setText(self.config.rsyncOptions())

    def store_values(self):
        """Store values from GUI into the config"""

        self.config.setNiceOnCron(self._cb_nice_on_cron.isChecked())
        self.config.setIoniceOnCron(self._cb_ionice_on_cron.isChecked())
        self.config.setIoniceOnUser(self._cb_ionice_on_user.isChecked())
        self.config.setNiceOnRemote(self._cb_nice_on_remote.isChecked())
        self.config.setIoniceOnRemote(self._cb_ionice_on_remote.isChecked())
        self.config.setNocacheOnLocal(self._cb_nocache_on_local.isChecked())
        self.config.setNocacheOnRemote(self._cb_nocache_on_remote.isChecked())
        self.config.setRedirectStdoutInCron(
            self._cb_redirect_stdout_cron.isChecked())
        self.config.setRedirectStderrInCron(
            self._cb_redirect_stderr_cron.isChecked())
        self.config.setBwlimit(self._cb_bwlimit.isChecked(),
                               self._spb_bwlimit.value())
        self.config.setPreserveAcl(self._cb_preserve_acl.isChecked())
        self.config.setPreserveXattr(self._cb_preserve_xattr.isChecked())

        self.config.setOneFileSystem(self._cb_one_filesystem.isChecked())
        self.config.setRsyncOptions(self._cb_restic_options.isChecked(),
                                    self._txt_restic_options.text())

    def update_items_state(self, enabled: bool):
        """Update state of widgets based on changed profile mode."""
        self._cb_nice_on_remote.setEnabled(enabled)
        self._cb_ionice_on_remote.setEnabled(enabled)
        self._cb_nocache_on_remote.setEnabled(enabled)
