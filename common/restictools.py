# SPDX-FileCopyrightText: © 2024-2026 Back In Time Restic Contributors
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time Restic" which is released
# under GNU General Public License v2 (GPLv2). See LICENSES directory or go
# to <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Wrapper around restic CLI operations.

All restic backends are supported natively:
  - local path: ``/path/to/repo``
  - SFTP: ``sftp:user@host:/path``
  - REST server: ``rest:https://host:port/``
  - Amazon S3: ``s3:s3.amazonaws.com/bucket``
  - Backblaze B2: ``b2:bucket:path``
  - Azure Blob: ``azure:container:path``
  - Google Cloud Storage: ``gs:bucket:/path``

Passwords are passed via the ``RESTIC_PASSWORD`` environment variable
(never on the command line).
"""
import json
import os
import subprocess
import shutil
from typing import Optional

import logger


class ResticError(Exception):
    """Raised when a restic command fails."""

    def __init__(self, message: str, returncode: int = 1,
                 stderr: str = ''):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def restic_binary() -> str:
    """Return the path to the restic binary.

    Returns:
        str: Full path to the restic binary.

    Raises:
        FileNotFoundError: If restic is not installed.
    """
    path = shutil.which('restic')
    if path is None:
        raise FileNotFoundError(
            'restic binary not found. Please install restic.')
    return path


def restic_version() -> str:
    """Return the installed restic version string.

    Returns:
        str: Version string, e.g. ``'0.16.4'``.

    Raises:
        ResticError: If the version check fails.
    """
    try:
        proc = subprocess.run(
            [restic_binary(), 'version'],
            capture_output=True, text=True, check=True
        )
        # Output is like: "restic 0.16.4 compiled with go1.21.5 on linux/amd64"
        parts = proc.stdout.strip().split()
        if len(parts) >= 2:
            return parts[1]
        return proc.stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise ResticError(
            'Failed to get restic version',
            returncode=exc.returncode,
            stderr=exc.stderr
        ) from exc


def _build_env(password: str,
               extra_env: Optional[dict[str, str]] = None) -> dict[str, str]:
    """Build environment dict for restic subprocess.

    The restic repository password is passed via ``RESTIC_PASSWORD``.
    Cloud backend credentials (AWS, B2, Azure, GCS) can be passed via
    ``extra_env``.

    Args:
        password: The restic repository password.
        extra_env: Additional environment variables (e.g. AWS_ACCESS_KEY_ID).

    Returns:
        dict: Environment for subprocess.
    """
    env = os.environ.copy()
    env['RESTIC_PASSWORD'] = password
    if extra_env:
        env.update(extra_env)
    return env


def _run_restic(args: list[str],
                password: str,
                extra_env: Optional[dict[str, str]] = None,
                capture_output: bool = True,
                json_output: bool = False,
                nice: bool = False,
                ionice: bool = False) -> subprocess.CompletedProcess:
    """Run a restic command.

    Args:
        args: Arguments to pass to restic (excluding the binary itself).
        password: Repository password.
        extra_env: Additional environment variables for cloud backends.
        capture_output: If True, capture stdout/stderr.
        json_output: If True, add ``--json`` flag.
        nice: If True, prepend ``nice -n 19``.
        ionice: If True, prepend ``ionice -c2 -n7``.

    Returns:
        subprocess.CompletedProcess: The completed process.

    Raises:
        ResticError: If the command exits with non-zero status.
    """
    cmd = []

    if ionice and shutil.which('ionice'):
        cmd.extend(['ionice', '-c2', '-n7'])

    if nice and shutil.which('nice'):
        cmd.extend(['nice', '-n19'])

    cmd.append(restic_binary())
    cmd.extend(args)

    if json_output and '--json' not in args:
        cmd.append('--json')

    env = _build_env(password, extra_env)

    logger.debug(f'Running restic: {" ".join(cmd)}')

    try:
        proc = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            env=env
        )
        if proc.returncode != 0:
            raise ResticError(
                f'restic command failed: {" ".join(args)}',
                returncode=proc.returncode,
                stderr=proc.stderr if capture_output else ''
            )
        return proc
    except FileNotFoundError as exc:
        raise ResticError(
            f'Failed to run restic: {exc}',
            returncode=127
        ) from exc


def restic_init(repo: str,
                password: str,
                extra_env: Optional[dict[str, str]] = None) -> bool:
    """Initialize a restic repository.

    Args:
        repo: Repository location (local path or remote URI).
        password: Repository password.
        extra_env: Additional env vars for cloud backends.

    Returns:
        bool: True if the repo was initialized successfully.

    Raises:
        ResticError: If initialization fails.
    """
    _run_restic(
        ['init', '--repo', repo],
        password=password,
        extra_env=extra_env
    )
    logger.info(f'Initialized restic repository: {repo}')
    return True


def restic_backup(repo: str,
                  password: str,
                  includes: list[str],
                  excludes: Optional[list[str]] = None,
                  tags: Optional[list[str]] = None,
                  one_file_system: bool = False,
                  extra_env: Optional[dict[str, str]] = None,
                  nice: bool = False,
                  ionice: bool = False,
                  limit_upload: int = 0,
                  limit_download: int = 0,
                  dry_run: bool = False) -> dict:
    """Run a restic backup.

    Args:
        repo: Repository location.
        password: Repository password.
        includes: List of paths to back up.
        excludes: List of exclude patterns.
        tags: List of tags to apply to the snapshot.
        one_file_system: If True, don't cross filesystem boundaries.
        extra_env: Additional env vars for cloud backends.
        nice: Run with low CPU priority.
        ionice: Run with low IO priority.
        limit_upload: Upload bandwidth limit in KiB/s (0 = unlimited).
        limit_download: Download bandwidth limit in KiB/s (0 = unlimited).
        dry_run: If True, perform a dry run.

    Returns:
        dict: Parsed JSON output from restic backup (summary).

    Raises:
        ResticError: If the backup fails.
    """
    args = ['backup', '--repo', repo]

    if tags:
        for tag in tags:
            args.extend(['--tag', tag])

    if excludes:
        for pattern in excludes:
            args.extend(['--exclude', pattern])

    if one_file_system:
        args.append('--one-file-system')

    if limit_upload > 0:
        args.extend(['--limit-upload', str(limit_upload)])

    if limit_download > 0:
        args.extend(['--limit-download', str(limit_download)])

    if dry_run:
        args.append('--dry-run')

    args.append('--json')
    args.extend(includes)

    proc = _run_restic(
        args,
        password=password,
        extra_env=extra_env,
        nice=nice,
        ionice=ionice
    )

    # Parse the JSON output - restic outputs one JSON object per line
    # The last line with "message_type":"summary" has the backup summary
    summary = {}
    for line in proc.stdout.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get('message_type') == 'summary':
                summary = data
        except json.JSONDecodeError:
            continue

    logger.info(f'Backup to {repo} completed')
    return summary


def restic_restore(repo: str,
                   password: str,
                   snapshot_id: str,
                   target: str,
                   includes: Optional[list[str]] = None,
                   excludes: Optional[list[str]] = None,
                   extra_env: Optional[dict[str, str]] = None) -> bool:
    """Restore files from a restic snapshot.

    Args:
        repo: Repository location.
        password: Repository password.
        snapshot_id: Snapshot ID or ``'latest'``.
        target: Target directory for restore.
        includes: Restore only these paths (optional).
        excludes: Exclude these paths (optional).
        extra_env: Additional env vars for cloud backends.

    Returns:
        bool: True if restore succeeded.

    Raises:
        ResticError: If the restore fails.
    """
    args = ['restore', snapshot_id, '--repo', repo, '--target', target]

    if includes:
        for path in includes:
            args.extend(['--include', path])

    if excludes:
        for path in excludes:
            args.extend(['--exclude', path])

    _run_restic(
        args,
        password=password,
        extra_env=extra_env
    )
    logger.info(f'Restored snapshot {snapshot_id} from {repo} to {target}')
    return True


def restic_snapshots(repo: str,
                     password: str,
                     tags: Optional[list[str]] = None,
                     extra_env: Optional[dict[str, str]] = None
                     ) -> list[dict]:
    """List snapshots in a restic repository.

    Args:
        repo: Repository location.
        password: Repository password.
        tags: Filter by tags (optional).
        extra_env: Additional env vars for cloud backends.

    Returns:
        list[dict]: List of snapshot dicts with keys like ``id``, ``time``,
                    ``hostname``, ``tags``, ``paths``, etc.

    Raises:
        ResticError: If the command fails.
    """
    args = ['snapshots', '--repo', repo, '--json']

    if tags:
        for tag in tags:
            args.extend(['--tag', tag])

    proc = _run_restic(
        args,
        password=password,
        extra_env=extra_env
    )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []


def restic_forget(repo: str,
                  password: str,
                  keep_last: Optional[int] = None,
                  keep_hourly: Optional[int] = None,
                  keep_daily: Optional[int] = None,
                  keep_weekly: Optional[int] = None,
                  keep_monthly: Optional[int] = None,
                  keep_yearly: Optional[int] = None,
                  keep_within: Optional[str] = None,
                  tags: Optional[list[str]] = None,
                  prune: bool = True,
                  dry_run: bool = False,
                  extra_env: Optional[dict[str, str]] = None
                  ) -> dict:
    """Remove old snapshots according to a retention policy.

    Args:
        repo: Repository location.
        password: Repository password.
        keep_last: Keep the last N snapshots.
        keep_hourly: Keep the last N hourly snapshots.
        keep_daily: Keep the last N daily snapshots.
        keep_weekly: Keep the last N weekly snapshots.
        keep_monthly: Keep the last N monthly snapshots.
        keep_yearly: Keep the last N yearly snapshots.
        keep_within: Keep all snapshots within a duration (e.g. ``'2y5m7d'``).
        tags: Only consider snapshots with these tags.
        prune: If True, also prune unreferenced data.
        dry_run: If True, perform a dry run.
        extra_env: Additional env vars for cloud backends.

    Returns:
        dict: Parsed JSON output from restic forget.

    Raises:
        ResticError: If the command fails.
    """
    args = ['forget', '--repo', repo]

    if keep_last is not None:
        args.extend(['--keep-last', str(keep_last)])
    if keep_hourly is not None:
        args.extend(['--keep-hourly', str(keep_hourly)])
    if keep_daily is not None:
        args.extend(['--keep-daily', str(keep_daily)])
    if keep_weekly is not None:
        args.extend(['--keep-weekly', str(keep_weekly)])
    if keep_monthly is not None:
        args.extend(['--keep-monthly', str(keep_monthly)])
    if keep_yearly is not None:
        args.extend(['--keep-yearly', str(keep_yearly)])
    if keep_within is not None:
        args.extend(['--keep-within', keep_within])

    if tags:
        for tag in tags:
            args.extend(['--tag', tag])

    if prune:
        args.append('--prune')

    if dry_run:
        args.append('--dry-run')

    args.append('--json')

    proc = _run_restic(
        args,
        password=password,
        extra_env=extra_env
    )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}


def restic_mount(repo: str,
                 password: str,
                 mount_point: str,
                 extra_env: Optional[dict[str, str]] = None
                 ) -> subprocess.Popen:
    """Mount a restic repository via FUSE.

    This returns a Popen object representing the background mount process.
    Call ``.terminate()`` or ``.kill()`` to unmount.

    Args:
        repo: Repository location.
        password: Repository password.
        mount_point: Local directory to mount to.
        extra_env: Additional env vars for cloud backends.

    Returns:
        subprocess.Popen: The background mount process.

    Raises:
        ResticError: If the mount fails to start.
    """
    cmd = [restic_binary(), 'mount', '--repo', repo, mount_point]
    env = _build_env(password, extra_env)

    os.makedirs(mount_point, exist_ok=True)

    logger.info(f'Mounting restic repo {repo} at {mount_point}')

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )

    return proc


def restic_check(repo: str,
                 password: str,
                 read_data: bool = False,
                 extra_env: Optional[dict[str, str]] = None) -> bool:
    """Verify the integrity of a restic repository.

    Args:
        repo: Repository location.
        password: Repository password.
        read_data: If True, also verify all data blobs.
        extra_env: Additional env vars for cloud backends.

    Returns:
        bool: True if the check passed.

    Raises:
        ResticError: If the check fails.
    """
    args = ['check', '--repo', repo]

    if read_data:
        args.append('--read-data')

    _run_restic(
        args,
        password=password,
        extra_env=extra_env
    )
    logger.info(f'Repository check passed: {repo}')
    return True


def build_repo_uri(mode: str, **kwargs) -> str:
    """Build a restic repository URI from mode and parameters.

    Args:
        mode: Backend mode (``'local'``, ``'sftp'``, ``'rest'``, ``'s3'``,
              ``'b2'``, ``'azure'``, ``'gs'``).
        **kwargs: Backend-specific parameters.

    Returns:
        str: The restic-compatible repository URI.

    Raises:
        ValueError: If the mode is unknown or required parameters are missing.
    """
    if mode == 'local':
        path = kwargs.get('path', '')
        if not path:
            raise ValueError("'path' is required for local backend")
        return path

    elif mode == 'sftp':
        user = kwargs.get('user', '')
        host = kwargs.get('host', '')
        port = kwargs.get('port', 22)
        path = kwargs.get('path', '')
        if not host:
            raise ValueError("'host' is required for sftp backend")
        uri = f'sftp:{user}@{host}' if user else f'sftp:{host}'
        if port and port != 22:
            uri += f':{port}'
        uri += f':{path}' if path else ':.'
        return uri

    elif mode == 'rest':
        url = kwargs.get('url', '')
        if not url:
            raise ValueError("'url' is required for rest backend")
        if not url.startswith('rest:'):
            url = f'rest:{url}'
        return url

    elif mode == 's3':
        endpoint = kwargs.get('endpoint', 's3.amazonaws.com')
        bucket = kwargs.get('bucket', '')
        path = kwargs.get('path', '')
        if not bucket:
            raise ValueError("'bucket' is required for s3 backend")
        uri = f's3:{endpoint}/{bucket}'
        if path:
            uri += f'/{path}'
        return uri

    elif mode == 'b2':
        bucket = kwargs.get('bucket', '')
        path = kwargs.get('path', '')
        if not bucket:
            raise ValueError("'bucket' is required for b2 backend")
        uri = f'b2:{bucket}'
        if path:
            uri += f':{path}'
        return uri

    elif mode == 'azure':
        container = kwargs.get('container', '')
        path = kwargs.get('path', '')
        if not container:
            raise ValueError("'container' is required for azure backend")
        uri = f'azure:{container}'
        if path:
            uri += f':{path}'
        return uri

    elif mode == 'gs':
        bucket = kwargs.get('bucket', '')
        path = kwargs.get('path', '')
        if not bucket:
            raise ValueError("'bucket' is required for gs backend")
        uri = f'gs:{bucket}:/'
        if path:
            uri = f'gs:{bucket}:/{path}'
        return uri

    else:
        raise ValueError(f"Unknown restic backend mode: '{mode}'")


def build_extra_env(mode: str, **kwargs) -> dict[str, str]:
    """Build extra environment variables for cloud backends.

    Args:
        mode: Backend mode.
        **kwargs: Backend-specific credentials.

    Returns:
        dict: Environment variables to set for the restic subprocess.
    """
    env = {}

    if mode == 's3':
        if kwargs.get('aws_access_key_id'):
            env['AWS_ACCESS_KEY_ID'] = kwargs['aws_access_key_id']
        if kwargs.get('aws_secret_access_key'):
            env['AWS_SECRET_ACCESS_KEY'] = kwargs['aws_secret_access_key']

    elif mode == 'b2':
        if kwargs.get('b2_account_id'):
            env['B2_ACCOUNT_ID'] = kwargs['b2_account_id']
        if kwargs.get('b2_account_key'):
            env['B2_ACCOUNT_KEY'] = kwargs['b2_account_key']

    elif mode == 'azure':
        if kwargs.get('azure_account_name'):
            env['AZURE_ACCOUNT_NAME'] = kwargs['azure_account_name']
        if kwargs.get('azure_account_key'):
            env['AZURE_ACCOUNT_KEY'] = kwargs['azure_account_key']

    elif mode == 'gs':
        if kwargs.get('google_application_credentials'):
            env['GOOGLE_APPLICATION_CREDENTIALS'] = \
                kwargs['google_application_credentials']
        if kwargs.get('google_project_id'):
            env['GOOGLE_PROJECT_ID'] = kwargs['google_project_id']

    return env
