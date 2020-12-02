import signal

import gevent
from optparse import OptionParser
from geventwebsocket.handler import WebSocketHandler
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


# run a local server with websocket support
def run_with_web_sockets(listen_address, port):
    server = gevent.pywsgi.WSGIServer((listen_address, port), app, handler_class=WebSocketHandler)

    # Shut down gracefully if running in a container that gets stopped.
    def shutdown(signum, frame):
        print('Shutting down on signal', signum)
        server.stop()
    signal.signal(signal.SIGTERM, shutdown)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


# if run as top-level script
if __name__ == '__main__':

    # process command arguments
    parser = OptionParser()
    parser.add_option('-w', '--run-as-worker', dest='run_as_worker', default='')
    parser.add_option('-s', '--enable-web-sockets',  dest='enable_web_sockets', action='store_true', default=False)
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
            balena_setup(app.config)
        if options.enable_web_sockets:
            print('running with websockets')
            run_with_web_sockets(options.listen_address, options.port)
        else:
            app.run(host=options.listen_address, port=options.port, debug=True)
