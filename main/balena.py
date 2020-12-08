"""
Bootstrap on-site instances of the server.

https://github.com/terraware/balena describes the expected configuration of the systems; the code
here assumes it's running on that hardware and software stack.

On-site servers need to bootstrap themselves without admin intervention before the server starts
listening for requests. The process needs to work for both the initial invocation on a pristine
system and on service restarts.

1. Mount or symlink the directory for local photo storage.
2. Wait for PostgreSQL to become available (since this container might be launched before the
   database starts listening for connections).
3. Initialize the database if needed.
4. If the TERRAWARE_ADMIN_EMAIL and TERRAWARE_ADMIN_PASSWORD environment variables are present,
   create the admin user or change its password.
5. If the TERRAWARE_ORGANIZATION_FOLDER, TERRAWARE_ORGANIZATION_NAME, TERRAWARE_CONTROLLER_FOLDER,
   and TERRAWARE_SECRET_KEY settings are present, create an organization and controller folder
   and configure the secret key as a valid API key for the controller.
"""
import logging
import os
import socket
import subprocess
import time
from typing import Dict
from urllib.parse import urlparse

from sqlalchemy.exc import IntegrityError

from main.app import db
from main.resources.models import Resource
from main.resources.resource_util import create_organization, create_system_resources
from main.users.admin import create_admin_user
from main.users.auth import create_key, find_key, login_validate, reset_user_password
from main.users.models import User

POSTGRESQL_SERVER_WAIT_SECS = 30
"""How long to block waiting for the PostgreSQL server to accept connections."""

logger = logging.getLogger(__name__)


def balena_setup(app_config: Dict[str, str]):
    """Bring the server online in a BalenaOS environment."""
    _configure_storage(app_config)
    _wait_for_database(app_config)
    _initialize_database()
    _create_or_update_admin_user()
    _bootstrap_controller_auth(app_config)


def _configure_storage(app_config: Dict[str, str]):
    """Mount the disk partition or symlink the Docker volume for local file storage."""
    storage_path = app_config.get('FILE_SYSTEM_STORAGE_PATH')
    if not storage_path:
        logger.info('FILE_SYSTEM_STORAGE_PATH not set, so no local storage mounted')
        return

    if os.environ.get('TERRAWARE_USE_INTERNAL_STORAGE', 'false')[:1].lower() in ['t', 'y', '1']:
        _symlink_docker_volume(storage_path)
    else:
        _mount_storage_device(storage_path)


def _mount_storage_device(storage_path):
    """Mount a filesystem from a disk device to use for file storage."""
    disk_device = os.environ.get('TERRAWARE_STORAGE_DISK', '/dev/md0p3')
    logger.info('Mounting storage device %s', disk_device)
    os.makedirs(storage_path, mode=0o777, exist_ok=True)
    result = subprocess.run(['mount', disk_device, storage_path], capture_output=True, text=True, check=False)
    if result.returncode:
        # In dev environments with live push, the first run of the server will have already
        # mounted the device in this container. We could explicitly check for the mount first,
        # but it's harmless to just let the "mount" command fail.
        if f'{disk_device} already mounted on {storage_path}' not in result.stderr:
            logger.error('Failed to mount data partition!')
            for line in result.stdout.split('\n'):
                if line != '':
                    logger.warning('mount stdout: %s', line)
            for line in result.stderr.split('\n'):
                if line != '':
                    logger.warning('mount stderr: %s', line)
            result.check_returncode()


def _symlink_docker_volume(storage_path):
    """Create the file storage directory as a symlink to a Docker volume.

    The Balena container configuration creates the volume and keeps it on the server's internal
    storage (SD card), so this effectively uses internal storage for data files.
    """
    logger.info('Using internal storage')
    storage_path_dirname = os.path.dirname(storage_path)
    os.makedirs(storage_path_dirname, mode=0o777, exist_ok=True)
    if os.path.exists(storage_path):
        os.unlink(storage_path)
    os.symlink('/file-storage-volume', storage_path)


def _wait_for_database(app_config: Dict[str, str]):
    """Wait until the PostgreSQL database starts accepting connections."""
    database_uri = app_config.get('SQLALCHEMY_DATABASE_URI')
    if not database_uri:
        raise Exception('No database URI configured')

    parts = urlparse(database_uri)
    if parts.scheme != 'postgres':
        logger.info("Don't know how to wait for database of type %s", parts.scheme)
        return

    port = parts.port or 5432
    wait_until = time.time() + POSTGRESQL_SERVER_WAIT_SECS

    while True:
        try:
            with socket.create_connection((parts.hostname, port), timeout=1):
                logger.info('PostgreSQL server is accepting connections')
                return
        except Exception as ex:  # pylint: disable=broad-except
            if time.time() >= wait_until:
                raise ex


def _initialize_database():
    """Populate the database with the required tables if needed."""
    # This is a no-op on already-initialized databases, so just do it every time.
    db.create_all()
    create_system_resources()


def _create_or_update_admin_user():
    """Add an admin user to the database if needed, or set the existing user's password."""
    admin_email = os.environ.get('TERRAWARE_ADMIN_EMAIL')
    admin_password = os.environ.get('TERRAWARE_ADMIN_PASSWORD')

    if admin_email and admin_password:
        if login_validate(admin_email, admin_password):
            # The admin already exists and has the right password.
            return

        try:
            create_admin_user(admin_email, admin_password)
            logger.info('Created admin user %s', admin_email)
        except IntegrityError:
            db.session.rollback()
            reset_user_password(admin_email, admin_password)
            logger.info('Updated admin password')
    else:
        logger.warning('No admin username/password configured')


def _bootstrap_controller_auth(app_config: Dict[str, str]):
    """Create an organization, controller folder, and API key."""
    org_name = app_config.get('TERRAWARE_ORGANIZATION_NAME')
    org_folder = app_config.get('TERRAWARE_ORGANIZATION_FOLDER')
    folder_name = app_config.get('TERRAWARE_CONTROLLER_FOLDER')
    secret_key = app_config.get('TERRAWARE_CONTROLLER_SECRET_KEY')

    if org_name and org_folder and folder_name and secret_key:
        org_resource = Resource.query.filter(Resource.name == org_folder, Resource.type == Resource.ORGANIZATION_FOLDER).one_or_none()
        if org_resource is not None:
            org_id = org_resource.id
        else:
            logger.info('Creating organization %s', org_name)
            org_id = create_organization(org_name, org_folder)

        controller_resource = Resource.query.filter(Resource.name == folder_name, Resource.type == Resource.CONTROLLER_FOLDER).one_or_none()
        if controller_resource is None:
            logger.info('Creating controller folder %s', folder_name)
            controller_resource = Resource(name=folder_name, type=Resource.CONTROLLER_FOLDER, parent_id=org_id)
            db.session.add(controller_resource)

        key_resource = find_key(secret_key)
        if key_resource is None:
            logger.info('Creating secret key for controller')
            admin_user_id = db.session.query(User.id).order_by(User.id).limit(1).scalar()
            (key_resource, _) = create_key(admin_user_id, org_id, None, controller_resource.id, secret_key)

        db.session.commit()
