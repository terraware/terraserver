import logging
import sys

from optparse import OptionParser

from main.app import app, db
from main.balena import balena_setup
from main.users.admin import create_admin_user
from main.resources.resource_util import create_system_resources

# import all views
from main.users import views
from main.api import views
from main.resources import views  # this should be last because it includes the catch-all resource viewer

# import all models
from main.users import models
from main.messages import models
from main.resources import models


# if run as top-level script
if __name__ == '__main__':

    # process command arguments
    parser = OptionParser()
    parser.add_option('-w', '--run-as-worker', dest='run_as_worker', default='')
    parser.add_option('-d', '--init-db', dest='init_db', action='store_true', default=False)
    parser.add_option('-a', '--create-admin', dest='create_admin', default='')
    parser.add_option('-m', '--migrate-db', dest='migrate_db', action='store_true', default=False)
    parser.add_option('-p', '--port', dest='port', type=int, default=5000)
    parser.add_option('-l', '--listen-address', dest='listen_address', default='127.0.0.1')
    parser.add_option('-b', '--balena', action='store_true', default=False)
    (options, args) = parser.parse_args()

    # DB operations
    if options.init_db:
        print('creating/updating database')
        db.create_all()
        create_system_resources()
    elif options.create_admin:
        parts = options.create_admin.split(':')
        email_address = parts[0]
        password = parts[1]
        create_admin_user(email_address, password)
        print('created system admin: %s' % email_address)
    elif options.migrate_db:
        pass

    # start the debug server
    else:
        if options.balena:
            try:
                balena_setup(app.config)
            except Exception as ex:  # pylint: disable=broad-except
                # Don't log the full stack trace because this is likely a database error, which means the
                # stack trace will be huge; the system will retry the app if it fails which would lead to
                # huge volumes of log spew.
                logging.error('Unable to complete Balena setup: %s', ex)
                sys.exit(1)

        app.run(host=options.listen_address, port=options.port, debug=True)
