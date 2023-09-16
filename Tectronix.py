# coding: utf-8
"""
Created on Aug 23, 2023

@author: sanin

s='s=%r;print(s%%s)';print(s%s)
"""
import http.client
import io
import socket
import threading

from PIL import Image
import sys
import time

if '../TangoUtils' not in sys.path: sys.path.append('../TangoUtils')

from log_exception import log_exception
from config_logger import config_logger
from isfread import isfread


def tec_connect(ip, timeout=None):
    connection = http.client.HTTPConnection(ip, timeout=timeout)
    return connection


def tec_request(connection, method, url, params, headers):
    connection.request(method, url, params, headers)
    response = connection.getresponse()
    if response.status != 200:
        return None
    return tec_read_response_data(response)


def tec_read_response_data(response):
    data = b''
    while True:
        d = response.read(1024)
        if not d:
            break
        data += d
    return data


def tec_send_command(connection, cmd, raw_response=False):
    params = ('COMMAND=' + cmd + '\n\rgpibsend=Send\n\rname=\n\r').encode()
    headers = {"Content-type": "text/plain",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"}
    connection.request("POST", "/Comm.html", params, headers)
    response = connection.getresponse()
    if response.status != 200:
        if raw_response:
            return None, response.status, None
        return None
    data = tec_read_response_data(response).decode()
    n = data.find('<TEXTAREA')
    if n < 0:
        if raw_response:
            return None, response.status, data
        return None
    n1 = data[n:].find('>')
    if n1 < 0:
        if raw_response:
            return None, response.status, data
        return None
    m = data.find('</TEXTAREA')
    if m < 0:
        if raw_response:
            return None, response.status, data
        return None
    if raw_response:
        return data[n + n1 + 1:m].strip(), response.status, data
    return data[n + n1 + 1:m].strip()


def tec_get_image_data(connection):
    params = b''
    headers = {"Accept": "image/avif,image/webp,*/*"}
    connection.request("GET", "/Image.png", params, headers)
    response = connection.getresponse()
    return tec_read_response_data(response)


def tec_get_image(connection):
    data = tec_get_image_data(connection)
    img = Image.open(io.BytesIO(data))
    return img


def tec_get_isf(connection, chan_number):
    s = 'command=select:ch%s on\r\ncommand=save:waveform:fileformat internal\r\nwfmsend=Get\r\n' % chan_number
    params = s.encode()
    headers = {"Accept": "text/html, application/xhtml+xml, image/jxr, */*",
               "Content-Type": "text/plain",
               "Cache-Control": "no-cache"}
    connection.request("POST", "/getwfm.isf", params, headers)
    response = connection.getresponse()
    return tec_read_response_data(response)


def tec_get_trace(connection, chan_number):
    isf = tec_get_isf(connection, chan_number)
    x, y, h = isfread(io.BytesIO(isf))
    return x, y, h, isf


class TectronixTDS:
    RECONNECT_TIMEOUT = 5.0
    default = {
        'VERBose': '0',  # 1 | 0 | ON | OFF
        'HEADer': '0',  # 1 | 0 | ON | OFF
        # '*LRN?': '',
        'ACQuire:STATE': '0',  # 1 | 0 | RUN | STOP
        'ACQuire:STOPAfter': 'SEQ',  # RUNSTop | SEQuence
        'ACQuire:MODe': 'SAMple',  # PEAKdetect | AVErage,
        'ACQuire:NUMACq?': '',
        # 'BUSY?': '',  # 0 | 1
        'CH1?': '',
        # 'CH1:BANdwidth': '',
        # 'CH1:COUPling': '',
        # 'CH1:DESKew': '0.0',
        # 'CH1:IMPedance': '',
        # 'CH1:OFFSet': '',
        # 'CH1:POSition': '',
        # 'CH1:PRObe?': '',
        # 'CH1:SCAle': '',
        'CH2?': '',
        # 'CH2:BANdwidth': '',
        # 'CH2:COUPling': '',
        # 'CH2:DESKew': '0.0',
        # 'CH2:IMPedance': '',
        # 'CH2:OFFSet': '',
        # 'CH2:POSition': '',
        # 'CH2:PRObe?': '',
        # 'CH2:SCAle': '',
        'CH3?': '',
        # 'CH3:BANdwidth': '',
        # 'CH3:COUPling': '',
        # 'CH3:DESKew': '0.0',
        # 'CH3:IMPedance': '',
        # 'CH3:OFFSet': '',
        # 'CH3:POSition': '',
        # 'CH3:PRObe?': '',
        # 'CH3:SCAle': '',
        'CH4?': '',
        # 'CH4:BANdwidth': '',
        # 'CH4:COUPling': '',
        # 'CH4:DESKew': '0.0',
        # 'CH4:IMPedance': '',
        # 'CH4:OFFSet': '',
        # 'CH4:POSition': '',
        # 'CH4:PRObe?': '',
        # 'CH4:SCAle': '',
        # 'DATE': '',
        # 'HORizontal:DELay:TIMe?': '',
        # 'HORizontal:MAIn:SCAle': '',  # sec / div
        # 'HORizontal:TRIGger:POSition': '',
        # 'ID?': '',
        'SELect?': '',
        # 'SELect:CH1': '',  # 1 | 0 | ON | OFF
        # 'SELect:CH2': '',  # 1 | 0 | ON | OFF
        # 'SELect:CH3': '',  # 1 | 0 | ON | OFF
        # 'SELect:CH4': '',  # 1 | 0 | ON | OFF
        # 'TIMe': '',
        # 'TRIGger': '',
        # 'TRIGger:MAIn:EDGE:COUPling': '',
        # 'TRIGger:MAIn:EDGE:SLOpe': '',
        # 'TRIGger:MAIn:EDGE:SOUrce': '',
        # 'TRIGger:MAIn:LEVel': '',
        # 'TRIGger:MAIn:MODe': '',  # AUTO | NORMAL
        # 'TRIGger:MAIn:TYPe': '',
        # 'TRIGger:STATE?': '',  # ARMED or not
        # 'VERBose': '0',
        # '*idn?': ''
    }

    def __init__(self, ip=None, timeout=1.0, config=None, logger=None):
        t0 = time.time()
        if logger is None:
            self.logger = config_logger()
        else:
            self.logger = logger
        self.lock = threading.Lock()
        self.config = {}
        if config is not None:
            self.config = config
        self.ip = '192.168.1.222'
        if ip is not None:
            self.ip = ip
        self.timeout = timeout
        self.response = ''
        self.connected = False
        self.reconnect_time = time.time() + self.RECONNECT_TIMEOUT
        self.connection = None
        # self.connection = tec_connect(self.ip, 2.0)
        # self.connected = True
        self.plots = {}
        self.tec_type = ''
        self.last_aq = ''
        self.connect(timeout=timeout)
        self.send_command('HEADer 0')
        self.set_config()
        if self.connected:
            self.logger.debug('%s at %s has been initialized (last_aq=%s) in %6.3f s',
                              self.tec_type, self.ip, self.last_aq, time.time() - t0)
        else:
            self.logger.info('Can not initialize tectronix oscilloscope')

    def __del__(self):
        if self.connection is not None:
            self.connection.close()

    def connect(self, timeout=None):
        if timeout is None:
            timeout = self.timeout
        self.timeout = timeout
        try:
            with self.lock:
                self.connection = tec_connect(self.ip, timeout=timeout)
            self.connected = True
            self.logger.debug('Connected')
        except KeyboardInterrupt:
            raise
        except:
            self.connected = False
            self.logger.debug('Connection failed')
        self.reconnect_time = time.time() + self.RECONNECT_TIMEOUT

    def send_command(self, cmd):
        result = self._send_command(cmd)
        if result is not None:
            return result
        self.logger.debug('Repeat %s', cmd)
        return self._send_command(cmd)

    def _send_command(self, cmd):
        result = None
        self.response = ('None', None, None)
        if not self.reconnect():
            return None
        t0 = time.time()
        try:
            with self.lock:
                result, status, data = tec_send_command(self.connection, cmd, True)
            self.response = (result, status, data)
            if result is not None:
                if result.startswith(':'):
                    with self.lock:
                        tec_send_command(self.connection, 'HEADer 0')
                        result, status, data = tec_send_command(self.connection, cmd, True)
                    self.response = (result, status, data)
                if cmd.endswith('?'):
                    self.config[cmd] = result
        except KeyboardInterrupt:
            raise
        except (socket.timeout, http.client.CannotSendRequest, ConnectionRefusedError):
            log_exception(self.logger, 'Send command %s exception', cmd)
            self.disconnect()
        self.logger.debug('%s -> "%s" %5.3f s', cmd, result, time.time() - t0)
        return result

    def reconnect(self):
        if self.connected:
            return True
        if self.reconnect_time < time.time():
            self.logger.debug('Reconnecting')
            self.connect()
            self.send_command('HEADer 0')
            return self.connected
        else:
            return False

    def disconnect(self):
        if not self.connected:
            return
        if self.connection is not None:
            with self.lock:
                self.connection.close()
        self.connected = False
        self.reconnect_time = time.time() + self.RECONNECT_TIMEOUT
        self.logger.debug('Disconnected')

    def set_config(self, config=None):
        t0 = time.time()
        if config is None:
            config = self.config
        cfg = self.default.copy()
        cfg.update(config)
        self.config = cfg
        for key in self.config:
            if key.endswith('?') or self.config[key] == '':
                if key.endswith("?"):
                    key1 = key
                else:
                    key1 = key + "?"
                self.config[key] = self.send_command(key1)
            else:
                self.send_command(key + ' ' + self.config[key])
        self.logger.debug('configuration total %6.3f s', time.time() - t0)
        if '*idn?' not in self.config or self.config['*idn?'] == '':
            self.config['*idn?'] = self.send_command('*idn?')
        if not self.connected:
            return
        if self.config['*idn?'] is not None:
            t = self.config['*idn?'].split(',')
            self.tec_type = ' '.join(t[0:2])
        if 'ACQuire:NUMACq' not in self.config:
            self.config['ACQuire:NUMACq'] = self.send_command('ACQuire:NUMACq?')
        self.last_aq = self.config['ACQuire:NUMACq']

    def get_data(self, ch_n):
        if not self.reconnect():
            return None
        with self.lock:
            return tec_get_trace(self.connection, ch_n)

    def get_image(self):
        with self.lock:
            if not self.connected:
                return
            try:
                return tec_get_image_data(self.connection)
            except KeyboardInterrupt:
                raise
            except:
                if not self.connected:
                    return

    def is_aq_finished(self):
        num_aq = self.send_command('ACQuire:NUMACq?')
        if num_aq is not None and num_aq != self.last_aq:
            self.logger.info('New shot detected %s -> %s', num_aq, self.last_aq)
            self.last_aq = num_aq
            return True
        return False

    def is_armed(self):
        st = self.send_command('TRIGger:STATE?')
        if st is not None:
            return st.upper().startswith('ARMED') or st.startswith('READY')
        return False

    def start_aq(self):
        if self.send_command('ACQuire:STATE 0') is None:
            return
        self.send_command('ACQuire:STATE 1')
        v = self.send_command('ACQuire:NUMACq?')
        if v is None:
            return
        self.last_aq = v
        return self.is_armed()

    def stop_aq(self):
        if self.send_command('ACQuire:STATE 0') is None:
            return None
        return True

    def is_aq_in_progress(self):
        st = self.send_command('BUSY?')
        if st is not None and st.upper().startswith('1'):
            return True
        return False

    def read_plots(self):
        self.plots = {}
        if not self.connected:
            return self.plots
        sel = self.send_command('SEL?').split(';')
        if not self.connected:
            return self.plots
        for i in range(4):
            if sel[i] == '1':
                # if self.send_command('SELect:CH%s?'%ch) == '1':
                x, y, h, isf = self.get_data(i + 1)
                self.plots[i + 1] = {'x': x, 'y': y, 'h': h, 'isf': isf}
        return self.plots

    def enable_channel(self, n):
        self.send_command('SELect:CH%s 1' % n)

    def disable_channel(self, n):
        self.send_command('SELect:CH%s 0' % n)

    def set_channel_state(self, n, state):
        if state:
            self.enable_channel(n)
        else:
            self.disable_channel(n)

    def get_channel_state(self, n):
        result = self.send_command('SELect:CH%s?' % n)
        if result == "1":
            return True
        return False

    def get_channel_scale(self, n):
        v = self.send_command('CH%s:SCAle?' % n)
        if v is not None:
            return float(v)
        return None

    def set_channel_scale(self, n, scale):
        v = self.send_command('CH%s:SCAle %s' % (n, scale))
        return v is not None

    def get_channel_offset(self, n):
        v = self.send_command('CH%s:OFFSet?' % n)
        if v is not None:
            return float(v)
        return None

    def set_channel_offset(self, n, offset):
        if n < 1 or n > 4:
            return None
        v = self.send_command('CH%s:OFFSet %s' % (n, offset))
        return v is not None

# tec_ip = "192.168.1.222"

# conn = http.client.HTTPConnection(tec_ip)
# conn.request("GET", "/")
# r1 = conn.getresponse()
# print(r1.status, r1.reason)
# params = urllib.parse.urlencode({'COMMAND': '*idn?', '@gpibsend': 'Send', '@name': ''})

# command = '*idn?'       # read device id
# command = 'CH1:COUP DC' # set channel 1 coupling to DC (AC, GND)
# command = 'CH1:IMP MEG' # set channel 1 impedance to 1MOhm (FIF)
# command = 'CH1:VOL 1.0' # set channel 1 voltage rang 1 V/dib (real)
# command = 'CH1:POS 2.0' # set channel 1 position +2 divisions (real)
# command = 'HOR:SCAL 0.1'  # sampling 0.1 s/div
# command = 'HOR:TRIG:POS 50.0'  # horiz. trigger position 50% of screen
# command = 'ID?'  # similar to *idn?
# command = '*LRN?'  # read all settings
# command = 'TRIG?'  # query trigger params
# command = 'TRIG FORC'  # force trigger
# command = 'TRIG:STATE?'  # trigger state


# print('Connecting')
# t0 = time.time()
# conn = tec_connect(tec_ip)
# print('Elapsed', time.time() - t0, 's')
#
# print('Sending command')
# t0 = time.time()
# result = tec_send_command(conn, 'TRIG:STATE?')
# print('Elapsed', time.time() - t0, 's')
# print(result)
#
# print('Reading image')
# t0 = time.time()
# result = tec_get_image(conn)
# print('Elapsed', time.time() - t0, 's')
#
# import matplotlib.pyplot as plt
#
# imgplot = plt.imshow(result)
# plt.show()
#
# print('Reading data')
# t0 = time.time()
# x, y, head = tec_get_data(conn, 2)
# print('Elapsed', time.time() - t0, 's')
# print(head)
# plt.plot(x, y)
# plt.xlabel('Time, s')
# plt.ylabel('Signal, V')
# plt.show()
#
# conn.close()
#
# print('Finished')
