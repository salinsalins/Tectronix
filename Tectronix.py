# coding: utf-8
"""
Created on Aug 23, 2023

@author: sanin

s='s=%r;print(s%%s)';print(s%s)
"""
import http.client
import io
import os
import socket
import sys
import threading
import time

from PIL import Image
import Moxa

u = os.path.dirname(os.path.realpath(sys.argv[0]))
util_path = os.path.join(os.path.split(u)[0], 'TangoUtils')
if util_path not in sys.path:
    sys.path.append(util_path)

from log_exception import log_exception
from config_logger import config_logger
from isfread import isfread


def tec_connect(ip, timeout=None, port=None):
    if port is None:
        connection = http.client.HTTPConnection(ip, timeout=timeout)
    else:
        if timeout is None:
            connection = Moxa.MoxaTCPComPort(ip, port)
        else:
            connection = Moxa.MoxaTCPComPort(ip, port, timeout=timeout)
    return connection


def tec_request(connection, method, url, params, headers):
    connection.request(method, url, params, headers)
    response = connection.getresponse()
    if response.status != 200:
        return None
    return tec_read_response_data(response)


def tec_read_response_data(response):
    try:
        d = response.read(1024)
    except KeyboardInterrupt:
        raise
    except:
        log_exception(config_logger())
        d = b''
    if not d:
        time.sleep(0.05)
    data = d
    while True:
        try:
            d = response.read(1024)
            if not d:
                break
            data += d
        except KeyboardInterrupt:
            raise
        except:
            break
    return data


def tec_send_command_port(connection, cmd, raw_response=False):
    if not isinstance(cmd, bytes):
        cmd = str(cmd).encode()
    if not cmd.endswith(b'\r\n'):
        cmd += b'\r\n'
    try:
        # connection.reset_input_buffer()
        # connection.reset_output_buffer()
        n = connection.write(cmd)
    except KeyboardInterrupt:
        raise
    except:
        print('!')
        # log_exception(config_logger())
        return ''
    # time.sleep(0.1)
    data = tec_read_response_data(connection)
    if raw_response:
        return data[:-1]
    try:
        return data[:-1].decode('ascii')
    except KeyboardInterrupt:
        raise
    except:
        print('!!')
        # log_exception(config_logger())
        pass
    return ''


def tec_send_command(connection, cmd, raw_response=False):
    if isinstance(connection, http.client.HTTPConnection):
        return tec_send_command_html(connection, cmd, raw_response)
    else:
        raw = tec_send_command_port(connection, cmd, raw_response)
        if not raw_response:
            return raw
        try:
            resp = raw.decode('ascii')
        except AttributeError:
            resp = raw
        except UnicodeDecodeError:
            resp = str(raw[:128])
        return resp, 200, raw


def tec_send_command_html(connection, cmd, raw_response=False):
    params = ('COMMAND=' + cmd + '\n\rgpibsend=Send\n\rname=\n\r').encode()
    headers = {"Content-type": "text/plain",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"}
    connection.request("POST", "/Comm.html", params, headers)
    response = connection.getresponse()
    if response.status != 200:
        if raw_response:
            return None, response.status, None
        return None
    raw = tec_read_response_data(response)
    out = None
    data = raw.decode()
    n = data.find('<TEXTAREA')
    if n >= 0:
        n1 = data[n:].find('>')
        if n1 >= 0:
            n2 = data.find('</TEXTAREA')
            if n2 >= n+n1+1:
                out = data[n+n1+1:n2].strip()
    if raw_response:
        return out, response.status, raw
    return out


def tec_get_image_data_port(connection):
    return b''


def tec_get_image_data_html(connection):
    params = b''
    headers = {"Accept": "image/avif,image/webp,*/*"}
    connection.request("GET", "/Image.png", params, headers)
    response = connection.getresponse()
    return tec_read_response_data(response)


def tec_get_image_data(connection):
    if isinstance(connection, http.client.HTTPConnection):
        return tec_get_image_data_html(connection)
    else:
        return tec_get_image_data_port(connection)


def tec_get_image(connection):
    data = tec_get_image_data(connection)
    img = Image.open(io.BytesIO(data))
    return img


def tec_get_isf_port(connection, chan_number):
    tec_send_command_port(connection, 'DATa:SOUrce CH%s'%chan_number)
    tec_send_command_port(connection, 'HEADER 1')
    data = tec_send_command_port(connection, 'WAVFrm?', raw_response=True)
    return data


def tec_get_isf(connection, chan_number):
    if isinstance(connection, http.client.HTTPConnection):
        return tec_get_isf_html(connection, chan_number)
    else:
        return tec_get_isf_port(connection, chan_number)


def tec_get_isf_html(connection, chan_number):
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

    def __init__(self, ip=None, timeout=1.0, config=None, port=None, logger=None):
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
        self.port = port
        self.timeout = timeout
        self.retries = 2
        self.response = ''
        self.connected = False
        self.reconnect_time = time.time() + self.RECONNECT_TIMEOUT
        self.connection = None
        self.plots = {}
        self.tec_type = ''
        self.last_aq = ''
        self.connect(timeout=timeout)
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
        try:
            with self.lock:
                self.connection = tec_connect(self.ip, timeout=timeout, port=self.port)
            self.connected = True
            self.logger.debug('Connected')
        except KeyboardInterrupt:
            raise
        except:
            self.connected = False
            self.logger.debug('Connection failed')
        self.reconnect_time = time.time() + self.RECONNECT_TIMEOUT

    def send_command(self, cmd):
        result = None
        n = 0
        while n < self.retries:
            n += 1
            result = self._send_command(cmd)
            result = self.strip_header(result)
            if result is not None:
                if cmd.endswith('?'):
                    self.config[cmd] = result
                break
            self.logger.debug('Repeat %s %s', cmd, n)
        return result

    def strip_header(self, result):
        if result is None:
            return None
        if isinstance(result, bytes):
            if not result.startswith(b':'):
                return result
            rs = result.split(b';')
            ri = []
            for r in rs:
                ri.append(r.split(b' ')[1])
            ro = b';'.join(ri)
        else:
            if not result.startswith(':'):
                return result
            rs = result.split(';')
            ri = []
            for r in rs:
                ri.append(r.split(' ')[1])
            ro = ';'.join(ri)
        return ro

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
            self.logger.debug('%s -> "%s" %5.3f s', cmd, result, time.time() - t0)
        except KeyboardInterrupt:
            raise
        except (socket.timeout, http.client.CannotSendRequest, ConnectionRefusedError):
            log_exception(self.logger, 'Command "%s" exception:', cmd, no_info=True)
            self.disconnect()
        return result

    def reconnect(self):
        if self.connected:
            return True
        if self.reconnect_time <= time.time():
            self.logger.debug('Reconnecting')
            self.connect()
            # self.send_command('HEADer 0')
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
        n = 0
        while n < self.retries:
            n += 1
            if self.reconnect():
                try:
                    with self.lock:
                        result = tec_get_trace(self.connection, ch_n)
                        if result:
                            return result
                except KeyboardInterrupt:
                    raise
                except:
                    pass
            self.logger.debug('Repeat %s', n)

    def get_image(self):
        n = 0
        while n < self.retries:
            n += 1
            if self.reconnect():
                try:
                    with self.lock:
                        result = tec_get_image_data(self.connection)
                        if result:
                            return result
                except KeyboardInterrupt:
                    raise
                except:
                    pass
            self.logger.debug('Repeat %s', n)

    def is_aq_finished(self):
        num_aq = self.send_command('ACQuire:NUMACq?')
        if num_aq is not None and num_aq != '' and num_aq != self.last_aq:
            self.logger.info('New shot detected %s -> %s', num_aq, self.last_aq)
            self.last_aq = num_aq
            return True
        return False

    def is_armed(self):
        st = self.send_command('TRIGger:STATE?')
        # READY TRIG SAV
        if st is not None:
            return st.upper().startswith('ARMED') or st.startswith('READY')
        return False

    def start_aq(self):
        if self.stop_aq() is None:
            return
        if self.send_command('ACQuire:STATE 1') is None:
            return
        t0 = time.time()
        while time.time() - t0 <= 1.0:
            v = self.send_command('ACQuire:NUMACq?')
            if v == '0':
                self.last_aq = v
                return True

    def stop_aq(self):
        if self.send_command('ACQuire:STATE 0') is None:
            return None
        return True

    def is_aq_in_progress(self):
        st = self.send_command('BUSY?')
        if st is not None and st.startswith('1'):
            return True
        return False

    def read_plots(self):
        self.plots = {}
        if not self.connected:
            return {}
        sel = self.send_command('SEL?')
        if sel is None:
            return {}
        sel = sel.split(';')
        for i in range(4):
            if sel[i] == '1':
                result = self.get_data(i + 1)
                if result is not None:
                    x, y, h, isf = result
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


def send_and_print(conn, cmd, **kwargs):
    t0 = time.time()
    raw_result = tec_send_command(conn, cmd, **kwargs)
    raw = kwargs.get('raw_response', False)
    if raw:
        result = raw_result[0]
    else:
        result = raw_result
    pr = result[:512]
    if len(result) > 127:
        if isinstance(pr, str):
            pr += ' ... '
        else:
            pr += b' ... '
    if isinstance(pr, str):
        pr = '"' + pr + '"'
    print('%12s'%cmd, ' ->', 'len=%s' % len(raw_result), '%6.3f s' % (time.time()-t0), pr)
    return result

if __name__ == '__main__':
    tec_ip = "192.168.1.223"
    # conn = http.client.HTTPConnection(tec_ip)
    conn = tec_connect(tec_ip, port=4000, timeout=0.01)

    send_and_print(conn, '*idn?')
    send_and_print(conn, 'DATa:SOUrce?')
    send_and_print(conn, 'DATa:ENCdg?')
    send_and_print(conn, 'DATa:WIDth?')
    send_and_print(conn, 'DATa:STARt?')
    send_and_print(conn, 'DATa:STOP?')
    send_and_print(conn, 'DATa:STOP 10000')
    send_and_print(conn, 'DATa:STOP?')
    # send_and_print(conn, 'HEAD 1')
    # send_and_print(conn, 'WFMPre?')
    # send_and_print(conn, 'CURVe?', raw_response=True)
    send_and_print(conn, 'BUSY?')
    send_and_print(conn, 'DATa:SOUrce CH%s'%1)
    send_and_print(conn, 'HEADER 1')
    send_and_print(conn, 'WFMPre?')
    # send_and_print(conn, 'WAVFrm?', raw_response=True)
    # data = tec_send_command_port(conn, 'WAVFrm?', raw_response=True)
    # print(data)
    # data = tec_get_isf_port(conn, 1)
    # print(data)
    conn.close()

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
