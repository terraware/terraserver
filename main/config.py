import os

import yaml


def defaults():
    """Return the default values for all the configuration settings.

    This also doubles as the list of environment variables.
    """
    return {
        'AUTOLOAD_EXTENSIONS': False,
        'CSRF_ENABLED': True,
        'CSRF_SESSION_KEY': '[Random String Here]',
        'DATABASE_CONNECT_OPTIONS': {},
        'DEBUG': True,
        'DEBUG_MESSAGING': False,
        'DOC_FILE_PREFIX': '',
        'EXTENSIONS': [],
        'EXTRA_NAV_ITEMS': '',
        'FILE_SYSTEM_STORAGE_PATH': '',
        'KEY_PREFIX': 'RHIZO',
        'MESSAGE_TOKEN_SALT': '[Random String Here]',
        'MESSAGING_LOG_PATH': '',
        'MQTT_HOST': '',
        'MQTT_PORT': 443,
        'MQTT_TLS': True,
        'OUTGOING_EMAIL_ADDRESS': '',
        'OUTGOING_EMAIL_PASSWORD': '',
        'OUTGOING_EMAIL_PORT': 587,
        'OUTGOING_EMAIL_SERVER': '',
        'OUTGOING_EMAIL_USER_NAME': '',
        'PRODUCTION': False,
        'RHIZO_SECRET_KEY': None,
        'S3_ACCESS_KEY': '',
        'S3_SECRET_KEY': '',
        'S3_STORAGE_BUCKET': '',
        'SALT': '[Random String Here]',
        'SECRET_KEY': '[Random String Here]',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///rhizo.db',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SSL': False,
        'SYSTEM_NAME': 'Rhizo Server',

        # If all of these are set and the server is running under Balena (--balena option),
        # it will create an organization, controller folder, and secret key for use by the
        # device manager.
        'TERRAWARE_CONTROLLER_FOLDER': None,
        'TERRAWARE_CONTROLLER_SECRET_KEY': None,
        'TERRAWARE_ORGANIZATION_FOLDER': None,
        'TERRAWARE_ORGANIZATION_NAME': None,

        'TEXT_FROM_PHONE_NUMBER': '',
        'THREADS_PER_PAGE': 8,
        'TWILIO_ACCOUNT_SID': '',
        'TWILIO_AUTH_TOKEN': '',

        # By default, the server tells the client to use MQTT_HOST:MQTT_PORT as the address of
        # the MQTT WebSocket interface. But this isn't always what we need:
        #
        # If the server and MQTT server are running in separate Docker containers on the same
        # host, then MQTT_HOST will point to the MQTT server's hostname on the Docker bridge
        # network but clients will need to connect to it using the host's external address.
        # In that case, set WEB_MQTT_SAME_HOST to True.
        #
        # If the server and MQTT server are both sitting behind a proxy, e.g., an Nginx instance
        # that does TLS termination, then the two will look like a single service to the client.
        # In that case, set both WEB_MQTT_SAME_HOST and WEB_MQTT_SAME_PORT to True.
        'WEB_MQTT_SAME_HOST': False,
        'WEB_MQTT_SAME_PORT': False,
    }


def environment():
    """Return a dict of configuration settings from environment variables.

    Environment variable names prefixed with "RHIZO_SERVER_" take precedence over environment
    variable names that are the same as the settings. That is, if both "RHIZO_SERVER_SSL" and "SSL"
    are set, the value of the former will be used.

    Values are parsed as YAML to allow non-string settings to be specified.

    If the "RHIZO_SERVER_DISABLE_ENVIRONMENT" environment variable is "true", no values
    will be read from the environment. This is mostly for use in unit tests to prevent tests from
    depending on the environment.
    """
    if os.environ.get('RHIZO_SERVER_DISABLE_ENVIRONMENT', '').lower() == 'true':
        return {}

    settings = {}

    for setting in defaults().keys():
        from_environ = os.environ.get('RHIZO_SERVER_' + setting, os.environ.get(setting, None))
        if from_environ:
            settings[setting] = yaml.load(from_environ, yaml.Loader)

    if os.environ.get('AUTOLOAD_EXTENSIONS') in ['True', 'true'] and os.path.exists('./extensions'):
        settings['EXTENSIONS'] = [o for o in os.listdir('./extensions/') if os.path.isdir(os.path.join('./extensions', o))]

    return settings
