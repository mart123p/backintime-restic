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
"""Module about the General tab"""
import os
from pathlib import Path
from typing import Any
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox,
                             QDialog,
                             QGridLayout,
                             QGroupBox,
                             QHBoxLayout,
                             QLabel,
                             QLineEdit,
                             QToolButton,
                             QVBoxLayout)
from config import Config
import tools
import logger
from exceptions import MountException
import mount
from bitbase import URL_ENCRYPT_TRANSITION
import version
import schedule
import qttools
import messagebox
from manageprofiles import combobox
from manageprofiles import schedulewidget
from bitwidgets import HLineWidget
from filedialog import FileDialog


class GeneralTab(QDialog):
    """Create the 'Generals' tab."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, parent):  # noqa: PLR0915
        # pylint: disable=too-many-statements
        super().__init__(parent=parent)

        self._parent_dialog = parent

        tab_layout = QVBoxLayout(self)

        # Snapshot mode
        self.mode = None

        vlayout = QVBoxLayout()
        tab_layout.addLayout(vlayout)

        self._combo_modes = self._snapshot_mode_combobox()
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel(_('Mode:'), self))
        hlayout.addWidget(self._combo_modes, 1)
        vlayout.addLayout(hlayout)

        # EncFS deprecation (#1734, #1735)
        self._lbl_encfs_warning = self._create_label_encfs_deprecation()
        tab_layout.addWidget(self._lbl_encfs_warning)
        tab_layout.addWidget(HLineWidget())

        # Where to save snapshots
        group_box = QGroupBox(self)
        self._group_mode_local = group_box
        group_box.setTitle(_('Where to save backups'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)

        hlayout = QHBoxLayout()
        vlayout.addLayout(hlayout)

        self._edit_backup_path = QLineEdit(self)
        self._edit_backup_path.setReadOnly(True)
        self._edit_backup_path.textChanged.connect(
            self._slot_full_path_changed)
        hlayout.addWidget(self._edit_backup_path)

        self._btn_backup_path = QToolButton(self)
        self._btn_backup_path.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._btn_backup_path.setIcon(self.icon.FOLDER)
        self._btn_backup_path.setMinimumSize(32, 28)
        hlayout.addWidget(self._btn_backup_path)
        self._btn_backup_path.clicked.connect(
            self._slot_snapshots_path_clicked)

        # --- Restic Backend Settings ---
        # SFTP backend
        group_box = QGroupBox(self)
        self._group_mode_sftp = group_box
        group_box.setTitle(_('SFTP Settings'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)

        self._lbl_sftp_host = QLabel(_('Host:'), self)
        hlayout1.addWidget(self._lbl_sftp_host)
        self._txt_sftp_host = QLineEdit(self)
        hlayout1.addWidget(self._txt_sftp_host)

        self._lbl_sftp_port = QLabel(_('Port:'), self)
        hlayout1.addWidget(self._lbl_sftp_port)
        self._txt_sftp_port = QLineEdit(self)
        self._txt_sftp_port.setText('22')
        hlayout1.addWidget(self._txt_sftp_port)

        self._lbl_sftp_user = QLabel(_('User:'), self)
        hlayout1.addWidget(self._lbl_sftp_user)
        self._txt_sftp_user = QLineEdit(self)
        hlayout1.addWidget(self._txt_sftp_user)

        self._lbl_sftp_path = QLabel(_('Path:'), self)
        hlayout2.addWidget(self._lbl_sftp_path)
        self._txt_sftp_path = QLineEdit(self)
        self._txt_sftp_path.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self._txt_sftp_path)

        # REST Server backend
        group_box = QGroupBox(self)
        self._group_mode_rest = group_box
        group_box.setTitle(_('REST Server Settings'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)

        self._lbl_rest_url = QLabel(_('URL:'), self)
        hlayout1.addWidget(self._lbl_rest_url)
        self._txt_rest_url = QLineEdit(self)
        self._txt_rest_url.setPlaceholderText('https://host:port/')
        hlayout1.addWidget(self._txt_rest_url)

        # S3 backend
        group_box = QGroupBox(self)
        self._group_mode_s3 = group_box
        group_box.setTitle(_('Amazon S3 Settings'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)
        grid = QGridLayout()
        vlayout.addLayout(grid)

        grid.addWidget(QLabel(_('Endpoint:'), self), 0, 0)
        self._txt_s3_endpoint = QLineEdit(self)
        self._txt_s3_endpoint.setPlaceholderText('s3.amazonaws.com')
        self._txt_s3_endpoint.setText('s3.amazonaws.com')
        grid.addWidget(self._txt_s3_endpoint, 0, 1)

        grid.addWidget(QLabel(_('Bucket:'), self), 1, 0)
        self._txt_s3_bucket = QLineEdit(self)
        grid.addWidget(self._txt_s3_bucket, 1, 1)

        grid.addWidget(QLabel(_('Path:'), self), 2, 0)
        self._txt_s3_path = QLineEdit(self)
        grid.addWidget(self._txt_s3_path, 2, 1)

        grid.addWidget(QLabel(_('Access Key ID:'), self), 3, 0)
        self._txt_s3_access_key = QLineEdit(self)
        grid.addWidget(self._txt_s3_access_key, 3, 1)

        grid.addWidget(QLabel(_('Secret Access Key:'), self), 4, 0)
        self._txt_s3_secret_key = QLineEdit(self)
        self._txt_s3_secret_key.setEchoMode(QLineEdit.EchoMode.Password)
        grid.addWidget(self._txt_s3_secret_key, 4, 1)

        # B2 backend
        group_box = QGroupBox(self)
        self._group_mode_b2 = group_box
        group_box.setTitle(_('Backblaze B2 Settings'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)
        grid = QGridLayout()
        vlayout.addLayout(grid)

        grid.addWidget(QLabel(_('Account ID:'), self), 0, 0)
        self._txt_b2_account_id = QLineEdit(self)
        grid.addWidget(self._txt_b2_account_id, 0, 1)

        grid.addWidget(QLabel(_('Account Key:'), self), 1, 0)
        self._txt_b2_account_key = QLineEdit(self)
        self._txt_b2_account_key.setEchoMode(QLineEdit.EchoMode.Password)
        grid.addWidget(self._txt_b2_account_key, 1, 1)

        grid.addWidget(QLabel(_('Bucket:'), self), 2, 0)
        self._txt_b2_bucket = QLineEdit(self)
        grid.addWidget(self._txt_b2_bucket, 2, 1)

        grid.addWidget(QLabel(_('Path:'), self), 3, 0)
        self._txt_b2_path = QLineEdit(self)
        grid.addWidget(self._txt_b2_path, 3, 1)

        # Azure backend
        group_box = QGroupBox(self)
        self._group_mode_azure = group_box
        group_box.setTitle(_('Azure Blob Storage Settings'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)
        grid = QGridLayout()
        vlayout.addLayout(grid)

        grid.addWidget(QLabel(_('Account Name:'), self), 0, 0)
        self._txt_azure_account_name = QLineEdit(self)
        grid.addWidget(self._txt_azure_account_name, 0, 1)

        grid.addWidget(QLabel(_('Account Key:'), self), 1, 0)
        self._txt_azure_account_key = QLineEdit(self)
        self._txt_azure_account_key.setEchoMode(QLineEdit.EchoMode.Password)
        grid.addWidget(self._txt_azure_account_key, 1, 1)

        grid.addWidget(QLabel(_('Container:'), self), 2, 0)
        self._txt_azure_container = QLineEdit(self)
        grid.addWidget(self._txt_azure_container, 2, 1)

        grid.addWidget(QLabel(_('Path:'), self), 3, 0)
        self._txt_azure_path = QLineEdit(self)
        grid.addWidget(self._txt_azure_path, 3, 1)

        # GCS backend
        group_box = QGroupBox(self)
        self._group_mode_gs = group_box
        group_box.setTitle(_('Google Cloud Storage Settings'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)
        grid = QGridLayout()
        vlayout.addLayout(grid)

        grid.addWidget(QLabel(_('Project ID:'), self), 0, 0)
        self._txt_gs_project_id = QLineEdit(self)
        grid.addWidget(self._txt_gs_project_id, 0, 1)

        grid.addWidget(QLabel(_('Bucket:'), self), 1, 0)
        self._txt_gs_bucket = QLineEdit(self)
        grid.addWidget(self._txt_gs_bucket, 1, 1)

        grid.addWidget(QLabel(_('Path:'), self), 2, 0)
        self._txt_gs_path = QLineEdit(self)
        grid.addWidget(self._txt_gs_path, 2, 1)

        vlayout.addWidget(QLabel(
            '<em>' +
            _('Note: Set GOOGLE_APPLICATION_CREDENTIALS environment '
              'variable to your service account JSON key file path.') +
            '</em>', self))

        # encfs
        self._group_mode_local_encfs = self._group_mode_local

        # gocryptfs
        self._group_mode_local_gocrypt = self._group_mode_local

        # password
        group_box = QGroupBox(self)
        self._group_password1 = group_box
        group_box.setTitle(_('Password'))
        tab_layout.addWidget(group_box)

        vlayout = QVBoxLayout(group_box)

        grid = QGridLayout()

        # Used for SSH passphrase & Encfs password
        self._lbl_password1 = QLabel(_('Password'), self)
        self._txt_password1 = QLineEdit(self)
        self._txt_password1.setEchoMode(QLineEdit.EchoMode.Password)

        # Used for Encfs password in "ssh encrypted" mode *rofl*
        self._lbl_password2 = QLabel(_('Password'), self)
        self._txt_password2 = QLineEdit(self)
        self._txt_password2.setEchoMode(QLineEdit.EchoMode.Password)

        # DEBUG
        if logger.DEBUG or version.IS_UNSTABLE_DEV_VERSION:
            self._lbl_password1.setToolTip('DEBUG - password 1')
            self._txt_password1.setToolTip('DEBUG - password 1')
            self._lbl_password2.setToolTip('DEBUG - password 2')
            self._txt_password2.setToolTip('DEBUG - password 2')

        grid.addWidget(self._lbl_password1, 0, 0)
        grid.addWidget(self._txt_password1, 0, 1)
        grid.addWidget(self._lbl_password2, 1, 0)
        grid.addWidget(self._txt_password2, 1, 1)
        vlayout.addLayout(grid)

        self._cb_password_save = QCheckBox(_('Save Password to Keyring'), self)
        vlayout.addWidget(self._cb_password_save)

        self._cb_password_use_cache = QCheckBox(
            _('Cache Password for Cron (Security '
              'issue: root can read password)'),
            self
        )
        vlayout.addWidget(self._cb_password_use_cache)

        self._keyring_supported = tools.keyringSupported()
        self._cb_password_save.setEnabled(self._keyring_supported)

        # mode change
        self._combo_modes.currentIndexChanged.connect(
            self._parent_dialog.slot_combo_modes_changed)

        # host, user, profile id
        group_box = QGroupBox(self)
        self._frame_advanced = group_box
        group_box.setTitle(_('Advanced'))
        tab_layout.addWidget(group_box)

        hlayout = QHBoxLayout(group_box)
        hlayout.addSpacing(12)

        vlayout2 = QVBoxLayout()
        hlayout.addLayout(vlayout2)

        hlayout2 = QHBoxLayout()
        vlayout2.addLayout(hlayout2)

        self._lbl_host = QLabel(_('Host:'), self)
        hlayout2.addWidget(self._lbl_host)
        self._txt_host = QLineEdit(self)
        self._txt_host.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self._txt_host)

        self._lbl_user = QLabel(_('User:'), self)
        hlayout2.addWidget(self._lbl_user)
        self._txt_user = QLineEdit(self)
        self._txt_user.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self._txt_user)

        self._lbl_profile = QLabel(_('Profile:'), self)
        hlayout2.addWidget(self._lbl_profile)
        self.txt_profile = QLineEdit(self)
        self.txt_profile.textChanged.connect(self._slot_full_path_changed)
        hlayout2.addWidget(self.txt_profile)

        self._lbl_full_path = QLabel(_('Full backup path:'), self)
        self._lbl_full_path.setWordWrap(True)
        vlayout2.addWidget(self._lbl_full_path)

        self._wdg_schedule = schedulewidget.ScheduleWidget(self)

        if schedule.CRONTAB_COMMAND is None:
            lbl_warning = qttools.create_info_label(
                text=_('Scheduling is disabled because no cron installation '
                       'was found. Please install cron to enable scheduled '
                       'backups.')
            )
            tab_layout.addWidget(lbl_warning)

            self._wdg_schedule.setHidden(True)

        tab_layout.addWidget(self._wdg_schedule)

        tab_layout.addStretch()

    @property
    def mode(self) -> str:
        """The backup mode"""
        return self._parent_dialog.mode

    @mode.setter
    def mode(self, value: str) -> None:
        self._parent_dialog.mode = value

    @property
    def config(self) -> Config:
        """The config instance"""
        return self._parent_dialog.config

    @property
    def icon(self):
        """Workaround. Remove until import of icon module is solved."""
        return self._parent_dialog.icon

    def _load_passwords(self):
        """A workaround to fix #2093 until the widgets are refactored and
        redesigned.
        """
        # password
        password_1 = self.config.password(
            mode=self.mode, pw_id=1, only_from_keyring=True)
        password_2 = self.config.password(
            mode=self.mode, pw_id=2, only_from_keyring=True)

        if password_1 is None:
            password_1 = ''

        if password_2 is None:
            password_2 = ''

        self._txt_password1.setText(password_1)
        self._txt_password2.setText(password_2)

        self._cb_password_save.setChecked(
            self._keyring_supported
            and self.config.passwordSave(mode=self.mode)
        )

        self._cb_password_use_cache.setChecked(
            self.config.passwordUseCache(mode=self.mode))

    def load_values(self) -> Any:
        """Set the values of the widgets regarding the current config."""
        backup_mode = self.config.snapshotsMode()
        self._combo_modes.select_by_data(backup_mode)

        # If the profile uses a deprecated backup mode (#1734)
        if 'encfs' in backup_mode:
            self._combo_modes.unhide_by_data(backup_mode)

        # local
        self._edit_backup_path.setText(
            self.config.snapshotsPath(mode='local'))

        # SFTP
        self._txt_sftp_host.setText(self.config.sftpHost())
        self._txt_sftp_port.setText(str(self.config.sftpPort()))
        self._txt_sftp_user.setText(self.config.sftpUser())
        self._txt_sftp_path.setText(self.config.sftpPath())

        # REST
        self._txt_rest_url.setText(self.config.restUrl())

        # S3
        self._txt_s3_endpoint.setText(self.config.s3Endpoint())
        self._txt_s3_bucket.setText(self.config.s3Bucket())
        self._txt_s3_path.setText(self.config.s3Path())
        self._txt_s3_access_key.setText(self.config.s3AccessKeyId())
        self._txt_s3_secret_key.setText(self.config.s3SecretAccessKey())

        # B2
        self._txt_b2_account_id.setText(self.config.b2AccountId())
        self._txt_b2_account_key.setText(self.config.b2AccountKey())
        self._txt_b2_bucket.setText(self.config.b2Bucket())
        self._txt_b2_path.setText(self.config.b2Path())

        # Azure
        self._txt_azure_account_name.setText(self.config.azureAccountName())
        self._txt_azure_account_key.setText(self.config.azureAccountKey())
        self._txt_azure_container.setText(self.config.azureContainer())
        self._txt_azure_path.setText(self.config.azurePath())

        # GCS
        self._txt_gs_project_id.setText(self.config.gsProjectId())
        self._txt_gs_bucket.setText(self.config.gsBucket())
        self._txt_gs_path.setText(self.config.gsPath())

        # local_encfs
        if self.mode == 'local_encfs':
            self._edit_backup_path.setText(self.config.localEncfsPath())

        # local_gocryptfs
        if self.mode == 'local_gocryptfs':
            self._edit_backup_path.setText(self.config.localGocryptfsPath())

        self._load_passwords()

        host, user, profile = self.config.hostUserProfile()
        self._txt_host.setText(host)
        self._txt_user.setText(user)
        self.txt_profile.setText(profile)

        # Schedule
        self._wdg_schedule.load_values(self.config)

    def _store_local_gocryptfs_destination_path(self) -> bool:
        """Path and password related to local gocryptfs profile.

        """

        # save local_gocryptfs
        if self.get_active_snapshots_mode() != 'local_gocryptfs':
            return True

        # backup path
        path = self._edit_backup_path.text()

        if path and Path(path).exists():
            self.config.setLocalGocryptfsPath(path)

        else:
            messagebox.warning(
                _('The backup destination path cannot be empty.'),
                _('Where to save backups'),
                self
            )
            return False

        # password
        password_1 = self._txt_password1.text()

        if not password_1:
            messagebox.warning(
                _('The encryption password cannot be empty.'),
                _('Encryption'),
                self
            )
            return False

        return True

    def store_values(self) -> bool:
        """Store the tab's values into the config instance.

        Returns:
            bool: Success or not.
        """
        mode = self.get_active_snapshots_mode()
        self.config.setSnapshotsMode(mode)

        # passwords
        password_1 = self._txt_password1.text()
        password_2 = self._txt_password2.text()

        mount_kwargs = {}

        if mode == 'local_encfs':
            mount_kwargs = {'password': password_1}

        self.config.setHostUserProfile(
            self._txt_host.text(),
            self._txt_user.text(),
            self.txt_profile.text()
        )

        # SFTP settings
        self.config.setSftpHost(self._txt_sftp_host.text())
        self.config.setSftpPort(self._txt_sftp_port.text())
        self.config.setSftpUser(self._txt_sftp_user.text())
        self.config.setSftpPath(self._txt_sftp_path.text())

        # REST settings
        self.config.setRestUrl(self._txt_rest_url.text())

        # S3 settings
        self.config.setS3Endpoint(self._txt_s3_endpoint.text())
        self.config.setS3Bucket(self._txt_s3_bucket.text())
        self.config.setS3Path(self._txt_s3_path.text())
        self.config.setS3AccessKeyId(self._txt_s3_access_key.text())
        self.config.setS3SecretAccessKey(self._txt_s3_secret_key.text())

        # B2 settings
        self.config.setB2AccountId(self._txt_b2_account_id.text())
        self.config.setB2AccountKey(self._txt_b2_account_key.text())
        self.config.setB2Bucket(self._txt_b2_bucket.text())
        self.config.setB2Path(self._txt_b2_path.text())

        # Azure settings
        self.config.setAzureAccountName(self._txt_azure_account_name.text())
        self.config.setAzureAccountKey(self._txt_azure_account_key.text())
        self.config.setAzureContainer(self._txt_azure_container.text())
        self.config.setAzurePath(self._txt_azure_path.text())

        # GCS settings
        self.config.setGsProjectId(self._txt_gs_project_id.text())
        self.config.setGsBucket(self._txt_gs_bucket.text())
        self.config.setGsPath(self._txt_gs_path.text())

        # save local_encfs
        self.config.setLocalEncfsPath(self._edit_backup_path.text())

        # _gocryptfs: path & password
        if self._store_local_gocryptfs_destination_path() is False:
            return False

        # schedule
        success = self._wdg_schedule.store_values(self.config)

        if success is False:
            return False

        # save password
        self.config.setPasswordSave(self._cb_password_save.isChecked(),
                                    mode=mode)
        self.config.setPasswordUseCache(
            self._cb_password_use_cache.isChecked(),
            mode=mode)
        self.config.setPassword(password_1, mode=mode)
        self.config.setPassword(password_2, mode=mode, pw_id=2)

        if mode not in ('local', 'local_encfs', 'local_gocryptfs'):
            # For remote restic backends, we don't need mount checking
            # Restic handles remote access natively
            pass
        elif mode != 'local':
            mnt = mount.Mount(cfg=self.config, tmp_mount=True, parent=self)
            hash_id = self._do_alot_pre_mount_checking(mnt, mount_kwargs)

            if hash_id is False:
                return False

        # snaphots_path
        if mode == 'local':
            self.config.set_snapshots_path(self._edit_backup_path.text())

        # Build and store the restic repo URI
        if mode in self.config.RESTIC_MODES:
            try:
                repo_uri = self.config.buildResticRepoUri()
                self.config.setResticRepo(repo_uri)
            except ValueError as ex:
                messagebox.critical(self, str(ex))
                return False

        # Store restic password
        if mode in self.config.RESTIC_MODES and password_1:
            self.config.setResticPassword(password_1)

        snapshots_mountpoint = self.config.get_snapshots_mountpoint(
            tmp_mount=True)

        if mode == 'local':
            success = tools.validate_and_prepare_snapshots_path(
                path=snapshots_mountpoint,
                host_user_profile=self.config.hostUserProfile(),
                mode=mode,
                copy_links=self.config.copyLinks(),
                error_handler=self.config.notifyError)

            if success is False:
                return False

        # umount
        if mode not in ('local',) + tuple(self.config.RESTIC_MODES):
            try:
                mnt.umount(hash_id=hash_id)

            except MountException as ex:
                messagebox.critical(self, str(ex))
                return False

        return True

    def _do_alot_pre_mount_checking(self, mnt, mount_kwargs):  # noqa: PLR0911
        """Initiate several checks related to mounting and similar tasks.

        Depending on the backup mode used different checks are initiated.

        Dev note (buhtz, 2024-09): The code is parked and ready to refactoring.

        Returns:
            bool: ``True`` if successful otherwise ``False``.
        """
        # pylint: disable=too-many-return-statements

        try:
            mode = self.config.snapshotsMode()
            if 'gocryptfs' in mode:
                if not mnt.get_backend(mode).isConfigured():
                    mnt.init_backend(mode=mode, **mount_kwargs)

        except MountException as ex:
            messagebox.critical(self, str(ex))

            return False

        try:
            # This will run several checks depending on the snapshots mode
            # used. Exceptions are raised if something goes wrong. On mode
            # "local" nothing is checked.
            mnt.preMountCheck(
                mode=self.config.snapshotsMode(),
                first_run=True,
                **mount_kwargs)

        except MountException as ex:
            messagebox.critical(self, str(ex))
            return False

        # okay, let's try to mount
        try:
            hash_id = mnt.mount(
                mode=self.config.snapshotsMode(),
                check=False,
                **mount_kwargs)

        except MountException as ex:
            messagebox.critical(self, str(ex))
            return False

        return hash_id

    def _snapshot_mode_combobox(self) -> combobox.BitComboBox:
        # Workaround until encryption transition (#1734) is finished.

        # # Find out if profiles using EncFS
        # all_used_modes = {
        #     self.config.snapshotsMode(pid) for pid in self.config.profiles()
        # }
        # print(f'{all_used_modes=}')  # DEBUG

        snapshot_modes = {}
        for key in self.config.SNAPSHOT_MODES:
            snapshot_modes[key] = self.config.SNAPSHOT_MODES[key][1]

        return combobox.BitComboBox(self, snapshot_modes)

    def _create_label_encfs_deprecation(self):
        # encfs deprecation warning (see #1734, #1735)

        whitepaper = f'<a href="{URL_ENCRYPT_TRANSITION}">'
        whitepaper = whitepaper + 'whitepaper' + '</a>'

        txt = [
            '<strong>Encrypted profiles using EncFS are no longer '
            'supported.</strong>',
            'New EncFS backup profiles can not be created anymore. '
            'Existing EncFS profiles are still displayed and '
            'supported for now, but EncFS support will be <strong>'
            'completely removed</strong> in a future release '
            '(expected around 2027).',
            'EncFS is considered insecure and is no longer actively '
            'maintained. For more information, see this '
            f'{whitepaper}.'
        ]
        txt = '<p>' + '</p><p>'.join(txt) + '</p>'

        return qttools.create_warning_label(txt, icon_scale_factor=3)

    def _slot_snapshots_path_clicked(self):
        old_path = Path(self._edit_backup_path.text())

        dlg = FileDialog(
            parent=self,
            title=_('Where to save backups'),
            show_hidden=True,
            allow_multiselection=False,
            dirs_only=True,
            start_dir=old_path)
        path = dlg.result()

        # nothing selected (Cancel)
        if not path:
            return

        # nothing changed
        if old_path and old_path == path:
            return

        # gocryptfs destination need to be empty
        if 'gocryptfs' in self.mode:
            # is not empty
            if not self._is_gocryptfs_path_empty(path):
                return

        # Really change?
        answer = messagebox.question(
            text=_('Really change the backup directory?'),
            widget_to_center_on=self)

        if not answer:
            return

        # Set the path
        self._edit_backup_path.setText(str(path))

    def _is_gocryptfs_path_empty(self, path: Path) -> bool:
        # is not empty
        if not any(path.iterdir()):
            return True

        messagebox.warning(
            '<p>'
            + _('The selected backup destination is not empty.')
            + '<p></p>'
            + _('It must be empty to use encryption.')
            + '</p>',
            widget_to_center_on=self
        )

        return False

    def _slot_full_path_changed(self, _text: Any):
        mode = self.mode

        if mode == 'sftp':
            path = self._txt_sftp_path.text()
        else:
            path = self._edit_backup_path.text()

        self._lbl_full_path.setText(
            _('Full backup path:') + ' ' +
            os.path.join(
                path,
                'backintime',
                self._txt_host.text(),
                self._txt_user.text(),
                self.txt_profile.text()
            ))

    def get_active_snapshots_mode(self) -> str:
        """Current profile mode"""
        return self._combo_modes.current_data

    def handle_combo_modes_changed(self):
        """Hide/show widget elements related to one of
        the snapshot modes.

        This is not a slot connected to a signal. But it is called by the
        parent dialog.
        """
        # Mode selected in the combo box
        active_mode = self.get_active_snapshots_mode()

        # New selected mode different from previous one?
        if active_mode != self.mode:

            self.mode = active_mode

            # Local path group (local, local_encfs, local_gocryptfs)
            self._group_mode_local.setVisible(
                active_mode in ('local', 'local_encfs', 'local_gocryptfs'))

            # Restic backend groups
            self._group_mode_sftp.setVisible(active_mode == 'sftp')
            self._group_mode_rest.setVisible(active_mode == 'rest')
            self._group_mode_s3.setVisible(active_mode == 's3')
            self._group_mode_b2.setVisible(active_mode == 'b2')
            self._group_mode_azure.setVisible(active_mode == 'azure')
            self._group_mode_gs.setVisible(active_mode == 'gs')

            self._wdg_schedule.allow_udev(
                active_mode in ('local', 'local_encfs', 'local_gocryptfs'))

            # gocryptfs destination need to be empty
            if 'gocryptfs' in self.mode:
                path = self._edit_backup_path.text()
                # dir exists and is not empty
                if path and any(Path(path).iterdir()):
                    self._edit_backup_path.setText('')

            # Don't offer deprecated modes (#1734)
            modes_to_hide = {'local_encfs'} - {active_mode}
            for hide in modes_to_hide:
                self._combo_modes.hide_by_data(hide)

        # A mode using password fields?
        if self.config.modeNeedPassword(active_mode):

            self._lbl_password1.setText(
                self.config.SNAPSHOT_MODES[active_mode][2] + ':')

            self._group_password1.show()

            if self.config.modeNeedPassword(active_mode, 2):
                self._lbl_password2.setText(
                    self.config.SNAPSHOT_MODES[active_mode][3] + ':')
                self._lbl_password2.show()
                self._txt_password2.show()

            else:
                self._lbl_password2.hide()
                self._txt_password2.hide()

            self._load_passwords()

        else:
            self._group_password1.hide()

        # EncFS deprecation warnings (see #1734)
        if active_mode == 'local_encfs':
            self._lbl_encfs_warning.show()

            # # Workaround to avoid showing the warning messagebox just when
            # # opening the manage profiles dialog.
            # if self._parent_dialog.isVisible():
            #     # Show the profile specific warning dialog only once per
            #     # profile.
            #     if profile_state.msg_encfs < ENCFS_MSG_STAGE:
            #         profile_state.msg_encfs = ENCFS_MSG_STAGE
            #         dlg = encfsmsgbox.EncfsCreateWarning(self)
            #         dlg.exec()

        else:
            self._lbl_encfs_warning.hide()
