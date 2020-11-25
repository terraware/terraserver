import time
import gevent
from gevent import monkey
monkey.patch_all()

# standard library imports
import logging
from collections import defaultdict

# other imports
from rhizo.controller import Controller
from devices.device_manager import DeviceManager

# initialize connection to rhizo server
c = Controller()

# initialize devices
d = DeviceManager(c)
if c.config.sim:
    d.load('config/sim_devices.csv')
else:
    d.load('config/devices.csv')
d.run()  # launch device polling greenlets


# handle messages from server
def handle_messages(message_type, params):
    if message_type == 'ohana_geni':
        new_state = bool(int(params['new_state']))
        device = d.find('ohana/generator-relay')
        if new_state:
            logging.info('turning on ohana generator')
            device.set_state(1)
        else:
            logging.info('turning off ohana generator')
            device.set_state(0)
    elif message_type == 'test_alarm':
        send_alarm_message('Test Alarm')
    else:
        pass
        # print('message type: %s' % type)
        # print(params)


c.messages.add_handler(handle_messages)


def send_alarm_message(alarm_name):
    recipients = c.config.ro_alarm_recipients
    for recipient in recipients:
        c.send_email(recipient, 'received ' + alarm_name, 'terraware notification: ' + alarm_name)


def average(*values):
    defined_values = [v for v in values if v is not None]
    if defined_values:
        return sum(defined_values)/len(defined_values)


def ro_status_text(status_code):
    if status_code == 0:
        status_text = 'standby'
    elif status_code == 1:
        status_text = 'starting'
    elif status_code == 2:
        status_text = 'running'
    elif status_code == 3:
        status_text = 'shutting down'
    else:
        status_text = 'unknown'
    return status_text


# loop until ctrl-c
def main_loop():
    global c  # rhizo client controler
    global d  # device manager
    prev_status_text_1 = None
    prev_status_text_2 = None
    alarm_sent = defaultdict(bool)
    last_watchdog_time = None

    logging.debug('starting main loop')
    while True:

        # compute ohana average SOC and turn on/off generator if needed
        ohana_soc_left = c.sequence.value('ohana/BMU-L/relative_state_of_charge')
        ohana_soc_right = c.sequence.value('ohana/BMU-R/relative_state_of_charge')
        avg = average(ohana_soc_left, ohana_soc_right)
        seq_vals = {}
        if avg:
            seq_vals[c.path_on_server() + '/ohana/average_soc'] = '%.2f' % avg
            lower_thresh = c.config.ohana_lower_soc_threshold
            upper_thresh = c.config.ohana_upper_soc_threshold
            relay_state = c.sequence.value('ohana/generator-relay/relay-1')
            if relay_state is not None:
                relay_state = int(relay_state)
                if avg < lower_thresh and relay_state == 0:
                    logging.info('ohana SOC (%.1f) below lower threshold (%.1f); turning on generator', avg, lower_thresh)
                    device = d.find('ohana/generator-relay')
                    device.set_state(1)
                if avg > upper_thresh and relay_state == 1:
                    logging.info('ohana SOC (%.1f) above upper threshold (%.1f); turning off generator', avg, upper_thresh)
                    device = d.find('ohana/generator-relay')
                    device.set_state(0)

        # compute garage main battery average SOC
        soc_1 = c.sequence.value('garage/BMU-1/relative_state_of_charge')
        soc_2 = c.sequence.value('garage/BMU-2/relative_state_of_charge')
        soc_3 = c.sequence.value('garage/BMU-3/relative_state_of_charge')
        soc_4 = c.sequence.value('garage/BMU-4/relative_state_of_charge')
        soc_5 = c.sequence.value('garage/BMU-5/relative_state_of_charge')
        avg = average(soc_1, soc_2, soc_3, soc_4, soc_5)
        if avg:
            seq_vals[c.path_on_server() + '/garage/average_soc'] = '%.2f' % avg

        # compute garage UPS/backup average SOC
        ups_soc_1 = c.sequence.value('garage/UPS-BMU-1/relative_state_of_charge')
        ups_soc_2 = c.sequence.value('garage/UPS-BMU-2/relative_state_of_charge')
        avg = average(ups_soc_1, ups_soc_2)
        if avg:
            seq_vals[c.path_on_server() + '/garage/ups_average_soc'] = '%.2f' % avg

        # send computed values to server
        if seq_vals:
            print('sending %d computed value(s) to server' % len(seq_vals))
            c.sequences.update_multiple(seq_vals)

        # compute RO status
        status_text_1 = ro_status_text(c.sequence.value('garage/RO/Array 1 Status Code'))
        status_text_2 = ro_status_text(c.sequence.value('garage/RO/Array 2 Status Code'))
        if status_text_1 != prev_status_text_1:
            c.sequences.update('garage/RO/Array 1 Status', status_text_1)
            prev_status_text_1 = status_text_1
        if status_text_2 != prev_status_text_2:
            c.sequences.update('garage/RO/Array 2 Status', status_text_2)
            prev_status_text_2 = status_text_2

        # check for RO alarms
        alarms = ['Array 1 Red Alarm', 'Array 2 Red Alarm', 'Array 1 Blue Alarm', 'Array 2 Blue Alarm']
        for alarm_name in alarms:
            value = c.sequence.value('garage/RO/' + alarm_name)
            if value and int(value):
                if not alarm_sent[alarm_name]:
                    logging.warning('RO alarm: %s', alarm_name)
                    send_alarm_message(alarm_name.lower())  # send email in lowercase to be a bit less alarming
                    alarm_sent[alarm_name] = True
            else:
                alarm_sent[alarm_name] = False

        # do watchdog check/update about once a minute
        t = time.time()
        if (last_watchdog_time is None) or t - last_watchdog_time > 55:
            d.watchdog_update()
            last_watchdog_time = t

        gevent.sleep(10)


# run a loop that catches errors in the main loop and restarts it as needed
while True:
    try:
        main_loop()
    except KeyboardInterrupt:
        print('exiting')
        break
    except Exception as e:
        logging.warning('exception in main loop: %s', e)
        gevent.sleep(5)
        logging.debug('restarting main loop')
