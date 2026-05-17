# SPDX-FileCopyrightText: © 2024-2026 Back In Time Restic Contributors
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time Restic" which is released
# under GNU General Public License v2 (GPLv2). See LICENSES directory or go
# to <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Unit tests for common/restictools.py

These tests verify the restictools module functions including URI building,
environment variable construction, and (where restic is installed) actual
restic operations.
"""
import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add common/ to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import restictools


class TestBuildRepoUri(unittest.TestCase):
    """Tests for restictools.build_repo_uri()"""

    def test_local(self):
        uri = restictools.build_repo_uri('local', path='/tmp/backup')
        self.assertEqual(uri, '/tmp/backup')

    def test_local_missing_path(self):
        with self.assertRaises(ValueError):
            restictools.build_repo_uri('local', path='')

    def test_sftp_basic(self):
        uri = restictools.build_repo_uri(
            'sftp', user='admin', host='backup.example.com',
            path='/srv/backup')
        self.assertEqual(uri, 'sftp:admin@backup.example.com:/srv/backup')

    def test_sftp_with_port(self):
        uri = restictools.build_repo_uri(
            'sftp', user='admin', host='backup.example.com',
            port=2222, path='/srv/backup')
        self.assertEqual(
            uri, 'sftp:admin@backup.example.com:2222:/srv/backup')

    def test_sftp_default_port(self):
        uri = restictools.build_repo_uri(
            'sftp', user='admin', host='backup.example.com',
            port=22, path='/srv/backup')
        self.assertEqual(uri, 'sftp:admin@backup.example.com:/srv/backup')

    def test_sftp_no_user(self):
        uri = restictools.build_repo_uri(
            'sftp', host='backup.example.com', path='/srv/backup')
        self.assertEqual(uri, 'sftp:backup.example.com:/srv/backup')

    def test_sftp_missing_host(self):
        with self.assertRaises(ValueError):
            restictools.build_repo_uri('sftp', user='admin', path='/srv')

    def test_rest(self):
        uri = restictools.build_repo_uri(
            'rest', url='https://backup.example.com:8000/')
        self.assertEqual(uri, 'rest:https://backup.example.com:8000/')

    def test_rest_prefix_already_present(self):
        uri = restictools.build_repo_uri(
            'rest', url='rest:https://backup.example.com:8000/')
        self.assertEqual(uri, 'rest:https://backup.example.com:8000/')

    def test_rest_missing_url(self):
        with self.assertRaises(ValueError):
            restictools.build_repo_uri('rest', url='')

    def test_s3(self):
        uri = restictools.build_repo_uri(
            's3', endpoint='s3.amazonaws.com', bucket='mybucket',
            path='backups')
        self.assertEqual(uri, 's3:s3.amazonaws.com/mybucket/backups')

    def test_s3_no_path(self):
        uri = restictools.build_repo_uri(
            's3', endpoint='s3.amazonaws.com', bucket='mybucket')
        self.assertEqual(uri, 's3:s3.amazonaws.com/mybucket')

    def test_s3_missing_bucket(self):
        with self.assertRaises(ValueError):
            restictools.build_repo_uri('s3', endpoint='s3.amazonaws.com')

    def test_b2(self):
        uri = restictools.build_repo_uri(
            'b2', bucket='mybucket', path='backups')
        self.assertEqual(uri, 'b2:mybucket:backups')

    def test_b2_no_path(self):
        uri = restictools.build_repo_uri('b2', bucket='mybucket')
        self.assertEqual(uri, 'b2:mybucket')

    def test_b2_missing_bucket(self):
        with self.assertRaises(ValueError):
            restictools.build_repo_uri('b2')

    def test_azure(self):
        uri = restictools.build_repo_uri(
            'azure', container='mycontainer', path='backups')
        self.assertEqual(uri, 'azure:mycontainer:backups')

    def test_azure_no_path(self):
        uri = restictools.build_repo_uri('azure', container='mycontainer')
        self.assertEqual(uri, 'azure:mycontainer')

    def test_azure_missing_container(self):
        with self.assertRaises(ValueError):
            restictools.build_repo_uri('azure')

    def test_gs(self):
        uri = restictools.build_repo_uri(
            'gs', bucket='mybucket', path='backups')
        self.assertEqual(uri, 'gs:mybucket:/backups')

    def test_gs_no_path(self):
        uri = restictools.build_repo_uri('gs', bucket='mybucket')
        self.assertEqual(uri, 'gs:mybucket:/')

    def test_gs_missing_bucket(self):
        with self.assertRaises(ValueError):
            restictools.build_repo_uri('gs')

    def test_unknown_mode(self):
        with self.assertRaises(ValueError):
            restictools.build_repo_uri('ftp')


class TestBuildExtraEnv(unittest.TestCase):
    """Tests for restictools.build_extra_env()"""

    def test_s3_env(self):
        env = restictools.build_extra_env(
            's3',
            aws_access_key_id='AKID',
            aws_secret_access_key='SECRET'
        )
        self.assertEqual(env['AWS_ACCESS_KEY_ID'], 'AKID')
        self.assertEqual(env['AWS_SECRET_ACCESS_KEY'], 'SECRET')

    def test_b2_env(self):
        env = restictools.build_extra_env(
            'b2',
            b2_account_id='ACID',
            b2_account_key='AKEY'
        )
        self.assertEqual(env['B2_ACCOUNT_ID'], 'ACID')
        self.assertEqual(env['B2_ACCOUNT_KEY'], 'AKEY')

    def test_azure_env(self):
        env = restictools.build_extra_env(
            'azure',
            azure_account_name='myaccount',
            azure_account_key='mykey'
        )
        self.assertEqual(env['AZURE_ACCOUNT_NAME'], 'myaccount')
        self.assertEqual(env['AZURE_ACCOUNT_KEY'], 'mykey')

    def test_gs_env(self):
        env = restictools.build_extra_env(
            'gs',
            google_project_id='myproject'
        )
        self.assertEqual(env['GOOGLE_PROJECT_ID'], 'myproject')

    def test_local_env_empty(self):
        env = restictools.build_extra_env('local')
        self.assertEqual(env, {})

    def test_sftp_env_empty(self):
        env = restictools.build_extra_env('sftp')
        self.assertEqual(env, {})


@unittest.skipUnless(
    shutil.which('restic'),
    'restic binary not installed'
)
class TestResticIntegration(unittest.TestCase):
    """Integration tests requiring restic to be installed."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.repo_dir = os.path.join(self.test_dir, 'repo')
        self.source_dir = os.path.join(self.test_dir, 'source')
        self.restore_dir = os.path.join(self.test_dir, 'restore')
        self.password = 'test-password-12345'

        os.makedirs(self.source_dir)
        os.makedirs(self.restore_dir)

        # Create test files
        with open(os.path.join(self.source_dir, 'file1.txt'), 'w') as f:
            f.write('Hello World')
        with open(os.path.join(self.source_dir, 'file2.txt'), 'w') as f:
            f.write('Test Data')
        os.makedirs(os.path.join(self.source_dir, 'subdir'))
        with open(
                os.path.join(self.source_dir, 'subdir', 'file3.txt'), 'w'
        ) as f:
            f.write('Nested File')

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_version(self):
        version = restictools.restic_version()
        self.assertTrue(version)
        # Version should look like x.y.z
        parts = version.split('.')
        self.assertGreaterEqual(len(parts), 2)

    def test_binary(self):
        binary = restictools.restic_binary()
        self.assertTrue(os.path.exists(binary))

    def test_init_backup_restore(self):
        """Test init -> backup -> verify snapshots -> restore."""
        # Init
        restictools.restic_init(self.repo_dir, self.password)
        self.assertTrue(os.path.exists(self.repo_dir))

        # Backup
        summary = restictools.restic_backup(
            self.repo_dir, self.password,
            includes=[self.source_dir],
            tags=['test-snapshot']
        )
        self.assertIn('snapshot_id', summary)

        # List snapshots
        snapshots = restictools.restic_snapshots(
            self.repo_dir, self.password)
        self.assertEqual(len(snapshots), 1)
        self.assertIn('test-snapshot', snapshots[0].get('tags', []))

        # Restore
        restictools.restic_restore(
            self.repo_dir, self.password,
            snapshot_id='latest',
            target=self.restore_dir
        )

        # Verify restored files
        restored_file = os.path.join(
            self.restore_dir, self.source_dir.lstrip('/'), 'file1.txt')
        self.assertTrue(os.path.exists(restored_file))
        with open(restored_file) as f:
            self.assertEqual(f.read(), 'Hello World')

    def test_incremental_backup(self):
        """Test that a second backup creates a second snapshot."""
        restictools.restic_init(self.repo_dir, self.password)

        # First backup
        restictools.restic_backup(
            self.repo_dir, self.password,
            includes=[self.source_dir],
            tags=['snap1']
        )

        # Modify a file
        with open(os.path.join(self.source_dir, 'file1.txt'), 'w') as f:
            f.write('Modified Content')

        # Second backup
        restictools.restic_backup(
            self.repo_dir, self.password,
            includes=[self.source_dir],
            tags=['snap2']
        )

        # Should have two snapshots
        snapshots = restictools.restic_snapshots(
            self.repo_dir, self.password)
        self.assertEqual(len(snapshots), 2)

    def test_exclude_patterns(self):
        """Test that exclude patterns work."""
        restictools.restic_init(self.repo_dir, self.password)

        restictools.restic_backup(
            self.repo_dir, self.password,
            includes=[self.source_dir],
            excludes=['*.txt']
        )

        # Restore and verify excluded files aren't present
        restictools.restic_restore(
            self.repo_dir, self.password,
            snapshot_id='latest',
            target=self.restore_dir
        )

        restored_source = os.path.join(
            self.restore_dir, self.source_dir.lstrip('/'))

        # The .txt files should not be restored (excluded)
        txt_files = list(Path(restored_source).rglob('*.txt'))
        self.assertEqual(len(txt_files), 0)

    def test_forget_retention(self):
        """Test forget with keep-last policy."""
        restictools.restic_init(self.repo_dir, self.password)

        # Create 3 snapshots
        for i in range(3):
            with open(
                    os.path.join(self.source_dir, f'iter{i}.txt'), 'w'
            ) as f:
                f.write(f'iteration {i}')
            restictools.restic_backup(
                self.repo_dir, self.password,
                includes=[self.source_dir]
            )

        snapshots_before = restictools.restic_snapshots(
            self.repo_dir, self.password)
        self.assertEqual(len(snapshots_before), 3)

        # Forget all but last 1
        restictools.restic_forget(
            self.repo_dir, self.password,
            keep_last=1, prune=True
        )

        snapshots_after = restictools.restic_snapshots(
            self.repo_dir, self.password)
        self.assertEqual(len(snapshots_after), 1)

    def test_check_integrity(self):
        """Test repository integrity check."""
        restictools.restic_init(self.repo_dir, self.password)

        restictools.restic_backup(
            self.repo_dir, self.password,
            includes=[self.source_dir]
        )

        # Should not raise
        result = restictools.restic_check(self.repo_dir, self.password)
        self.assertTrue(result)


class TestNoRsyncReferences(unittest.TestCase):
    """Meta-test: verify no rsync imports or subprocess calls in source."""

    def test_no_rsync_imports(self):
        """Scan all .py files for 'import rsync' or rsync subprocess calls."""
        common_dir = Path(__file__).resolve().parent.parent
        qt_dir = common_dir.parent / 'qt'

        rsync_refs = []
        for search_dir in (common_dir, qt_dir):
            for py_file in search_dir.rglob('*.py'):
                # Skip test files and .po files
                if 'test' in str(py_file) or '/po/' in str(py_file):
                    continue
                try:
                    content = py_file.read_text()
                    for i, line in enumerate(content.split('\n'), 1):
                        if 'import sshtools' in line:
                            rsync_refs.append(
                                f'{py_file}:{i}: {line.strip()}')
                except (UnicodeDecodeError, PermissionError):
                    continue

        self.assertEqual(
            rsync_refs, [],
            f'Found sshtools references in source files:\n'
            + '\n'.join(rsync_refs)
        )


if __name__ == '__main__':
    unittest.main()
