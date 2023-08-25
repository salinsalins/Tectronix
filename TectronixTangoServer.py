#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tectronix oscilloscope1000 series tango device server

"""
import json
import logging
import sys
import time

import numpy
import tango
from tango import AttrQuality, AttrWriteType, DispLevel, DevState
from tango.server import attribute, command

if '../TangoUtils' not in sys.path: sys.path.append('../TangoUtils')

from TangoServerPrototype import TangoServerPrototype
from log_exception import log_exception

from Tectronix import TectronixTDS


empty_array = numpy.zeros(0, dtype=numpy.float32)


class TectronixTangoServer(TangoServerPrototype):
    server_version_value = '0.1'
    server_name_value = 'Tectronix oscilloscope (TDS3014) Tango device server'
    device_list = []

    # scalar attributes
    tecronix_type = attribute(label="type", dtype=str,
                             display_level=DispLevel.OPERATOR,
                             access=AttrWriteType.READ,
                             unit="", format="%s",
                             doc="Type of Tectronix oscilloscope")

    trigger = attribute(label="trigger", dtype=float,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ_WRITE,
                        unit="", format="%10.0f",
                        doc="Trigger index")

    horizontal_scale = attribute(label="horizontal_scale", dtype=float,
                         display_level=DispLevel.OPERATOR,
                         access=AttrWriteType.READ_WRITE,
                         unit="s/div", format="%f",
                         doc="Horizontal scale in sec / div")

    record_in_progress = attribute(label="record_in_progress", dtype=bool,
                                   display_level=DispLevel.OPERATOR,
                                   access=AttrWriteType.READ_WRITE,
                                   unit="", format="",
                                   doc="Is record operation in progress")

    data_ready = attribute(label="data_ready", dtype=bool,
                           display_level=DispLevel.OPERATOR,
                           access=AttrWriteType.READ,
                           unit="", format="",
                           doc="Is data ready for reading")

    ch1_state = attribute(label="channel1_state", dtype=bool,
                         display_level=DispLevel.OPERATOR,
                         access=AttrWriteType.READ_WRITE,
                         unit="", format="%s",
                         doc='Enable/Disable state of the channel')

    ch2_state = attribute(label="channel2_state", dtype=bool,
                         display_level=DispLevel.OPERATOR,
                         access=AttrWriteType.READ_WRITE,
                         unit="", format="%s",
                         doc='Enable/Disable state of the channel')

    ch3_state = attribute(label="channel3_state", dtype=bool,
                         display_level=DispLevel.OPERATOR,
                         access=AttrWriteType.READ_WRITE,
                         unit="", format="%s",
                         doc='Enable/Disable state of the channel')

    ch4_state = attribute(label="channel4_state", dtype=bool,
                         display_level=DispLevel.OPERATOR,
                         access=AttrWriteType.READ_WRITE,
                         unit="", format="%s",
                         doc='Enable/Disable state of the channel')

    start_time = attribute(label="start_time", dtype=float,
                           display_level=DispLevel.OPERATOR,
                           access=AttrWriteType.READ,
                           unit="s", format="%f",
                           doc="Recording start time - UNIX seconds")

    stop_time = attribute(label="stop_time", dtype=float,
                          display_level=DispLevel.OPERATOR,
                          access=AttrWriteType.READ,
                          unit="s", format="%f",
                          doc="Recording stop time - UNIX seconds")
    # !!!!!!!!!!!!!!!!!!!!!
    # Channel numbering starts from 1 !!! (according manufacturer manuals and API)
    # !!!!!!!!!!!!!!!!!!!!!
    # channels for recorded ADC samples
    chany01 = attribute(label="Channel_01", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="V", format="%5.3f",
                        doc="Channel 01 data in Volts")

    chany02 = attribute(label="Channel_02", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="V", format="%5.3f",
                        doc="Channel 02 data in Volts")

    chany03 = attribute(label="Channel_03", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="V", format="%5.3f",
                        doc="Channel 03 data in Volts")

    chany04 = attribute(label="Channel_04", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="V", format="%5.3f",
                        doc="Channel 04 data in Volts")

    # channels for ADC times 32 bit floats in s
    chanx01 = attribute(label="Channel_01_times", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%5.3f",
                        doc="Times for channel counts. 32 bit floats in s")

    chanx02 = attribute(label="Channel_02_times", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%5.3f",
                        doc="Times for channel counts. 32 bit floats in s")

    chanx03 = attribute(label="Channel_03_times", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%5.3f",
                        doc="Times for channel counts. 32 bit floats in s")

    chanx04 = attribute(label="Channel_04_times", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%5.3f",
                        doc="Times for channel counts. 32 bit floats in s")

    def init_device(self):
        self.tec = None
        self.x1 = empty_array
        self.x2 = empty_array
        self.x3 = empty_array
        self.x4 = empty_array
        self.y1 = empty_array
        self.y2 = empty_array
        self.y3 = empty_array
        self.y4 = empty_array
        self.horizontal_scale_value = 1.0
        self.trigger_value = 0.0
        self.device_type_str = "Unknown Tectronix device"
        self.device_name = ''
        self.record_initiated = False
        self.data_ready_value = False
        self.init_result = None
        self.reconnect_enabled = False
        self.reconnect_timeout = time.time() + 5.0
        self.reconnect_count = 3
        # trigger
        self.trigger_auto = 0
        # set logger and device proxy in super and then call self.set_config()
        super().init_device()
        if self not in TectronixTangoServer.device_list:
            TectronixTangoServer.device_list.append(self)
        self.log_level.set_write_value(logging.getLevelName(self.logger.getEffectiveLevel()))
        self.configure_tango_logging()

    def set_config(self):
        try:
            self.device_name = self.get_name()
            self.set_state(DevState.INIT)
            self.set_status('Initialization')
            self.reconnect_enabled = self.config.get('auto_reconnect', False)
            # create Tectronix oscilloscope1000 device
            ip = self.config.get('ip', '192.168.1.222')
            config = self.config.get('settings', {})
            if isinstance(config, str):
                config = json.loads(config)
            self.tec = TectronixTDS(ip=ip, config=config)
            # change device logger to class logger
            self.tec.logger = self.logger
            # open Tectronix oscilloscope
            # self.tec.open()
            self.set_state(DevState.OPEN)
            self.set_status('Tectronix oscilloscope opened')
            # self.Tectronix oscilloscope.get_info()
            self.device_type_str = self.tec.tec_type
            super().set_config()
            if self.device_type_str != "Unknown Tectronix device":
                self.init_result = None
                self.horizontal_scale_value = float(self.tec.send_command('HORizontal:MAIn:SCAle?'))
                self.trigger_value = float(self.tec.send_command('HORizontal:TRIGger:POSition?'))
                msg = '%s %s has been initialized' % (self.device_name, self.device_type_str)
                self.logger.info(msg)
                self.set_state(DevState.STANDBY)
                self.set_status('Tectronix oscilloscope has been initialized successfully')
        except Exception as ex:
            self.init_result = ex
            log_exception(self, 'Exception initiating Tectronix oscilloscope %s', self.device_name)
            self.set_state(DevState.FAULT)
            self.set_status('Error initializing Tectronix oscilloscope')
            return False
        return True

    def delete_device(self):
        try:
            self.tec.stop_aq()
        except KeyboardInterrupt:
            raise
        except:
            pass
        # try:
        #     self.Tectronix oscilloscope.close()
        # except KeyboardInterrupt:
        #     raise
        # except:
        #     pass
        self.record_initiated = False
        self.data_ready_value = False
        self.set_state(DevState.CLOSE)
        self.set_status('Tectronix oscilloscope has been stopped')
        msg = '%s Tectronix oscilloscope has been deleted' % self.device_name
        self.logger.info(msg)

    def read_tecronix_type(self):
        return self.device_type_str

    def read_ch1_state(self):
        return self.tec.get_channel_state(1)

    def read_ch2_state(self):
        return self.tec.get_channel_state(2)

    def read_ch3_state(self):
        return self.tec.get_channel_state(3)

    def read_ch4_state(self):
        return self.tec.get_channel_state(4)

    def write_ch1_state(self, state):
        self.tec.set_channel_state(1, bool(state))

    def write_ch2_state(self, state):
        self.tec.set_channel_state(2, bool(state))

    def write_ch3_state(self, state):
        self.tec.set_channel_state(3, bool(state))

    def write_ch4_state(self, state):
        self.tec.set_channel_state(4, bool(state))

    def read_horizontal_scale(self):
        return self.horizontal_scale_value

    def write_horizontal_scale(self,  v):
        self.horizontal_scale_value = v
        self.tec.send_command('HORizontal:MAIn:SCAle ' + str(v))

    def read_trigger(self):
        return self.trigger_value

    def write_trigger(self , v):
        self.trigger_value = v
        self.tec.send_command('HORizontal:TRIGger:POSition ' + str(v))

    def read_record_in_progress(self):
        return self.tec.send_command('BUSY?') == '1'

    def write_record_in_progress(self, value: bool):
        if value:
            if self.record_initiated:
                return
            else:
                self.start_recording()
        else:
            if self.record_initiated:
                self.stop_recording()
            else:
                return





    def read_data_ready(self):
        return self.data_ready_value

    def read_start_time(self):
        return self.recording_start_time

    def read_stop_time(self):
        return self.recording_stop_time

    def read_chany01(self):
        return self.y1

    def read_chany02(self):
        return self.y2

    def read_chany03(self):
        return self.y3

    def read_chany04(self):
        return self.y4


    def read_chanx01(self):
        return self.x1

    def read_chanx02(self):
        return self.x2

    def read_chanx03(self):
        return self.x3

    def read_chanx04(self):
        return self.x4

    @command(dtype_in=None, dtype_out=bool)
    def ready(self):
        self.assert_open()
        try:
            return self.ready()
        except KeyboardInterrupt:
            raise
        except:
            log_exception(self, '%s Readiness query error', self.device_name, level=logging.WARNING)
            return False

    @command(dtype_in=int, dtype_out=bool)
    def _start(self, value=0):
        self.assert_open()
        try:
            if value > 0:
                if self.record_initiated:
                    msg = '%s Can not start - record in progress' % self.device_name
                    self.logger.info(msg)
                    return False
            self.start_recording()
            self.record_initiated = True
            self.data_ready_value = False
            self.set_state(DevState.RUNNING)
            self.set_status('Recording is in progress')
            msg = '%s Recording started' % self.device_name
            self.logger.info(msg)
            return True
        except KeyboardInterrupt:
            raise
        except:
            self.record_initiated = False
            self.set_state(DevState.FAULT)
            self.set_status('Recording start fault')
            log_exception(self, '%s Recording start error' % self.device_name, level=logging.WARNING)
            return False

    @command(dtype_in=None, dtype_out=bool)
    def start_recording(self):
        self.stop_recording()
        return self._start()

    @command(dtype_in=None)
    def apply_config(self):
        # set channels for measurements, sampling interval, number of points for channel, creates data arrays
        self.set_sampling()
        # set additional properties for channels:
        self.configure_channels()
        # set trigger
        self.set_trigger()

    @command(dtype_in=None)
    def stop_recording(self):
        try:
            self.stop()
            self.set_state(DevState.STANDBY)
            self.set_status('Recording has been stopped')
            self.logger.info('%s Recording has been stopped' % self.device_name)
        except KeyboardInterrupt:
            raise
        except:
            self.set_state(DevState.FAULT)
            self.set_status('Recording stop error')
            log_exception(self, '%s Recording stop error' % self.device_name, level=logging.WARNING)
        self.record_initiated = False
        self.data_ready_value = False

   def assert_open(self):
        if self.opened:
            if self.last_status == pl1000.PICO_STATUS['PICO_OK'] or \
                    self.last_status == pl1000.PICO_STATUS['PICO_BUSY']:
                return True
            if self.last_status == pl1000.PICO_STATUS['PICO_NOT_RESPONDING'] or \
                    self.last_status == pl1000.PICO_STATUS['PICO_NOT_FOUND']:
                self..opened = False
                self.record_initiated = False
                self.data_ready_value = False
                self.reconnect()
                return self.opened
        else:
            self.record_initiated = False
            self.data_ready_value = False
            self.reconnect()
            return self.opened

    def set_channel_properties(self, channel, props=None):
        try:
            attrib = channel
            if isinstance(channel, int):
                attrib = getattr(self, name_from_number(channel))
            elif isinstance(channel, str):
                attrib = getattr(self, str(channel))
            if props is None:
                props = {}
            prop = attrib.get_properties()
            prop.display_unit = self.Tectronix oscilloscope.scale
            prop.max_value = self.Tectronix oscilloscope.max_adc
            try:
                for p in props:
                    if hasattr(prop, p):
                        setattr(prop, p, props[p])
            except KeyboardInterrupt:
                raise
            except:
                pass
            attrib.set_properties(prop)
        except KeyboardInterrupt:
            raise
        except:
            log_exception(self, 'Properties set error')

    def configure_channels(self):
        for i in range(1, 17):
            self.set_channel_properties(name_from_number(i))
            self.set_channel_properties(name_from_number(i, xy='x'),
                                        {'display_unit': 1.0,
                                         'max_value': (self.Tectronix oscilloscope.points - 1) * self.Tectronix oscilloscope.sampling})
        self.set_channel_properties(self.raw_data)
        self.channel_record_time_us.set_write_value(self.config['channel_record_time_us'])
        self.points_per_channel.set_write_value(self.config['points_per_channel'])
        self.channels.set_write_value(self.config['channels'])
        self.record_in_progress.set_write_value(self.record_initiated)

    def set_sampling(self):
        self.assert_Tectronix oscilloscope_open()
        channels_list = list_from_str(self.config.get('channels', '[1]'))
        points = int(self.config.get('points_per_channel', 1000))
        record_us = int(self.config.get('channel_record_time_us', 10000))
        self.Tectronix oscilloscope.set_timing(channels_list, points, record_us)
        self.data_ready_value = False
        self.config['points_per_channel'] = self.Tectronix oscilloscope.points
        self.set_device_property('points_per_channel', str(self.config['points_per_channel']))
        self.config['channel_record_time_us'] = self.Tectronix oscilloscope.record_us
        self.set_device_property('channel_record_time_us', str(self.config['channel_record_time_us']))

    def set_trigger(self):
        self.assert_Tectronix oscilloscope_open()
        # read trigger parameters
        self.trigger_enabled = self.config.get('trigger_enabled', 0)
        self.trigger_auto = self.config.get('trigger_auto', 0)
        self.trigger_auto_ms = self.config.get('trigger_auto_ms', 0)
        self.trigger_channel = self.config.get('trigger_channel', 1)
        self.trigger_direction = self.config.get('trigger_direction', 0)
        self.trigger_threshold = self.config.get('trigger_threshold', 2048)
        self.trigger_hysteresis = self.config.get('trigger_hysteresis', 100)
        self.trigger_delay = self.config.get('trigger_delay', 10.0)
        # set trigger
        self.Tectronix oscilloscope.set_trigger(self.trigger_enabled, self.trigger_channel,
                                 self.trigger_direction, self.trigger_threshold,
                                 self.trigger_hysteresis, self.trigger_delay,
                                 self.trigger_auto, self.trigger_auto_ms)

    def read(self):
        if not self.record_initiated:
            return False
        self.assert_Tectronix oscilloscope_open()
        try:
            if self.Tectronix oscilloscope.ready():
                self.Tectronix oscilloscope.read()
                self.record_initiated = False
                self.data_ready_value = True
                self.logger.info('%s Data has been red' % self.device_name)
                self.set_state(DevState.STANDBY)
                self.set_status('Data is ready')
        except KeyboardInterrupt:
            raise
        except:
            self.record_initiated = False
            self.set_state(DevState.Fault)
            self.set_status('Data read error')
            log_exception(self, '%s Reading data error' % self.device_name, level=logging.WARNING)

    def reconnect(self):
        if not self.reconnect_enabled:
            return
        self.reconnect_count -= 1
        if self.reconnect_count > 0:
            return
        if time.time() - self.reconnect_timeout <= 0.0:
            return
        self.logger.debug('Reconnecting ...')
        self.reconnect_count = 3
        self.reconnect_timeout = time.time() + 5.0
        self.delete_device()
        self.init_device()
        if self.Tectronix oscilloscope.opened:
            self.set_state(DevState.STANDBY)
            self.set_status('Reconnected successfully')
            self.logger.info('Reconnected successfully')
        else:
            self.set_state(DevState.FAULT)
            self.set_status('Reconnection Error')
            self.logger.warning('Reconnection Error')


def looping():
    global t0
    time.sleep(0.010)
    for dev in TectronixTangoServer.device_list:
        time.sleep(0.001)
        if time.time() - t0 > 1.0:
            t0 = time.time()
            dev.assert_open()
        if dev.record_initiated:
            try:
                if dev.ready():
                    msg = '%s Recording finished, data is ready' % dev.device_name
                    dev.logger.info(msg)
                    dev.read()
            except KeyboardInterrupt:
                raise
            except:
                log_exception(dev, '%s Reading data error' % dev.device_name, level=logging.WARNING)



if __name__ == "__main__":
    t0 = time.time()
    TectronixTangoServer.run_server(event_loop=looping)
