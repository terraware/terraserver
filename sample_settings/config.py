# Configuration options. You can set these by modifying a copy of this file and uncommenting the
# ones you want to change, or by setting environment variables.
#
# Environment variable names may be prefixed with "RHIZO_SERVER_". Environment variables are parsed
# as YAML. If you want to keep the copy of this file somewhere other than "settings/config.py",
# set the RHIZO_SERVER_SETTINGS environment variable to its full path.

# If True, write to S3 buckets and send watchdog email.
# PRODUCTION = False

# If True, log additional diagnostics.
# DEBUG = True

# enables ssl_required decorator
# SSL = False

# SYSTEM_NAME = 'Rhizo Server'

# If True, look for extensions in main/extensions and load them automatically.
# AUTOLOAD_EXTENSIONS = False

# List of specific extensions to load. Only used if AUTOLOAD_EXTENSIONS is not True.
# EXTENSIONS = []

# Address of MQTT server to connect to.
# MQTT_HOST = ''

# format for postgres: 'postgres://[username]:[password]@[hostname]/[db]'
# SQLALCHEMY_DATABASE_URI = 'sqlite:///rhizo.db'

# SQLALCHEMY_TRACK_MODIFICATIONS = False
# DATABASE_CONNECT_OPTIONS = {}
# THREADS_PER_PAGE = 8
# DEBUG_MESSAGING = False
# MESSAGING_LOG_PATH = ''
# CSRF_ENABLED = True

# replace this if you want to identify your keys more easily
# KEY_PREFIX = 'RHIZO'

# Twilio credentials and sending phone number.
# TWILIO_ACCOUNT_SID = ''
# TWILIO_AUTH_TOKEN = ''
# TEXT_FROM_PHONE_NUMBER = ''

# Credentials and bucket name for S3 storage. If S3_ACCESS_KEY is empty or None, the server
# will look in the standard places for credentials ($HOME/.aws/config, AWS_* environment variables,
# EC2 instance metadata, etc.)
# S3_ACCESS_KEY = ''
# S3_SECRET_KEY = ''
# S3_STORAGE_BUCKET = ''

# these OUTGOING_EMAIL settings are required if you want to invite people to create accounts
# OUTGOING_EMAIL_ADDRESS = ''
# OUTGOING_EMAIL_USER_NAME = ''
# OUTGOING_EMAIL_PASSWORD = ''
# OUTGOING_EMAIL_SERVER = ''
# OUTGOING_EMAIL_PORT = 587

# EXTRA_NAV_ITEMS = ''
# DOC_FILE_PREFIX = ''

#
# Random keys are generated by prep_config.py; override if needed.
#

CSRF_SESSION_KEY = '[Random String Here]'

# used internally by flask
SECRET_KEY = '[Random String Here]'

# used for hashing passwords and API keys
SALT = '[Random String Here]'

# used for generating tokens for MQTT authentication
MESSAGE_TOKEN_SALT = '[Random String Here]'
