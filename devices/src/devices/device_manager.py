import csv
import time
import gevent
import logging
from .relay_device import RelayDevice
from .modbus_device import ModbusDevice


# manages a set of devices; each device handles a connection to physical hardware
class DeviceManager(object):

    def __init__(self, controller):
        self.controller = controller
        self.devices = []
        self.start_time = None
        self.diagnostic_mode = controller.config.device_diagnostics

    # initialize devices using a CSV file
    def load(self, device_list_file_name):
        with open(device_list_file_name) as csvfile:
            reader = csv.DictReader(csvfile)
            for line in reader:
                if int(line['enabled']):
                    device_type = line['type']
                    settings = line['settings']
                    server_path = line['server_path']
                    host = line['host']
                    port = int(line['port'])
                    polling_interval = int(line['polling_interval'])
                    if device_type == 'relay':
                        device = RelayDevice(self.controller, server_path, host, port, settings, polling_interval, self.diagnostic_mode)
                    elif device_type == 'modbus':
                        device = ModbusDevice(self.controller, server_path, host, port, settings, polling_interval, self.diagnostic_mode)
                    else:
                        print('unrecognized device type: %s' % device_type)
                    self.devices.append(device)

    # launch device polling greenlets
    def run(self):
        for device in self.devices:
            device.greenlet = gevent.spawn(device.run)
        self.start_time = time.time()

    # find a device by server_path
    def find(self, server_path):
        for device in self.devices:
            if device.server_path() == server_path:
                return device

    # check on devices; restart them as needed; if all is good, send watchdog message to server
    def watchdog_update(self):
        auto_restart = False  # disable auto-restart for now; we seem to occasionally get duplicate device greenlets

        # if it has been a while since startup, start checking device updates
        if time.time() - self.start_time > 30:
            devices_ok = True
            for device in self.devices:
                if device._last_update_time is None or time.time() - device._last_update_time > 10 * 60:
                    logging.info('no recent update for device %s', device._server_path)
                    if auto_restart:
                        device.greenlet.kill()  # this doesn't seem to work; we end up with multiple greenlets for the same device
                        device.greenlet = gevent.spawn(device.run)
                    devices_ok = False

            # if all devices are updating, send a watchdog message to server
            if devices_ok:
                self.controller.send_message('watchdog', {})
