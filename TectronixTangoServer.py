#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tectronix oscilloscope tango device server

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
    server_version_value = '1.0'
    server_name_value = 'Tectronix oscilloscope (TDS3014) Tango device server'
    device_list = []

    # scalar attributes
    tecronix_type = attribute(label="type", dtype=str,
                              display_level=DispLevel.OPERATOR,
                              access=AttrWriteType.READ,
                              unit="", format="%s",
                              doc="Type of Tectronix oscilloscope")

    trigger_position = attribute(label="trigger", dtype=float,
                                 display_level=DispLevel.OPERATOR,
                                 min_value=-50.0, max_value=100.0,
                                 access=AttrWriteType.READ_WRITE,
                                 unit="%", format="%5.1f",
                                 doc="Trigger position % of screen")

    horizontal_scale = attribute(label="horizontal_scale", dtype=float,
                                 display_level=DispLevel.OPERATOR,
                                 min_value=1.0e-7, max_value=10.0,
                                 access=AttrWriteType.READ_WRITE,
                                 unit="s/div", format="%12.6f",
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

    force_trigger = attribute(label="force_trigger", dtype=bool,
                          display_level=DispLevel.OPERATOR,
                          access=AttrWriteType.WRITE,
                          unit="", format="",
                          doc='Force trigger')

    ch1_scale = attribute(label="channel1_scale", dtype=float,
                          display_level=DispLevel.OPERATOR,
                          access=AttrWriteType.READ_WRITE,
                          min_value=1.0e-6, max_value=5.0,
                          unit="V/div", format="%12.6f",
                          doc='Vertical scale the channel in Volts per division')

    ch1_offset = attribute(label="channel1_offset", dtype=float,
                           display_level=DispLevel.OPERATOR,
                           access=AttrWriteType.READ_WRITE,
                           min_value=-5.0, max_value=5.0,
                           unit="div", format="%5.2f",
                           doc='Vertical offset for the channel in divisions')

    ch1_state = attribute(label="channel1_state", dtype=bool,
                          display_level=DispLevel.OPERATOR,
                          access=AttrWriteType.READ_WRITE,
                          unit="", format="",
                          doc='Enable/Disable state of the channel')

    ch2_state = attribute(label="channel2_state", dtype=bool,
                          display_level=DispLevel.OPERATOR,
                          access=AttrWriteType.READ_WRITE,
                          unit="", format="",
                          doc='Enable/Disable state of the channel')

    ch3_state = attribute(label="channel3_state", dtype=bool,
                          display_level=DispLevel.OPERATOR,
                          access=AttrWriteType.READ_WRITE,
                          unit="", format="",
                          doc='Enable/Disable state of the channel')

    ch4_state = attribute(label="channel4_state", dtype=bool,
                          display_level=DispLevel.OPERATOR,
                          access=AttrWriteType.READ_WRITE,
                          unit="", format="",
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
                        unit="V", format="%12.6f",
                        doc="Channel 01 data in Volts")

    chany02 = attribute(label="Channel_02", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="V", format="%12.6f",
                        doc="Channel 02 data in Volts")

    chany03 = attribute(label="Channel_03", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="V", format="%12.6f",
                        doc="Channel 03 data in Volts")

    chany04 = attribute(label="Channel_04", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="V", format="%12.6f",
                        doc="Channel 04 data in Volts")

    # channels for ADC times 32 bit floats in s
    chanx01 = attribute(label="Channel_01_times", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%12.6f",
                        doc="Times for channel counts. 32 bit floats in s")

    chanx02 = attribute(label="Channel_02_times", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%12.6f",
                        doc="Times for channel counts. 32 bit floats in s")

    chanx03 = attribute(label="Channel_03_times", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%12.6f",
                        doc="Times for channel counts. 32 bit floats in s")

    chanx04 = attribute(label="Channel_04_times", dtype=[numpy.float32],
                        max_dim_x=10000,
                        max_dim_y=0,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="s", format="%12.6f",
                        doc="Times for channel counts. 32 bit floats in s")

    def init_device(self):
        self.tec = None
        self.x = [empty_array] * 4
        self.y = [empty_array] * 4
        self.hor_sc = 1.0
        self.trig_val = 0.0
        self.scles = [0.0] * 4
        self.offsets = [0.0] * 4
        self.device_type_value = "Unknown Tectronix device"
        self.device_name = ''
        self.record_start_time = 0.0
        self.record_stop_time = 0.0
        self.record_initiated = False
        self.data_ready_value = False
        self.init_result = None
        self.reconnect_enabled = False
        self.reconnect_timeout = time.time() + 5.0
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
            super().set_config()
            #
            self.pre = f'{self.name} Tectronix server'
            self.device_name = self.get_name()
            self.set_state(DevState.INIT, 'Initialization')
            # self.reconnect_enabled = self.config.get('auto_reconnect', False)
            # create Tectronix oscilloscope device
            ip = self.config.get('ip', '192.168.1.222')
            config = self.config.get('settings', {})
            if isinstance(config, str):
                config = json.loads(config)
            self.tec = TectronixTDS(ip=ip, config=config)
            # change device logger to class logger
            self.tec.logger = self.logger
            self.device_type_value = self.tec.tec_type
            #
            if self.connected:
                if self.read_horizontal_scale() is None:
                    return False
                self.horizontal_scale.set_write_value(self.hor_sc)
                if self.read_trigger_position() is None:
                    return False
                self.trigger_position.set_write_value(self.trig_val)
                self.init_result = None
                msg = '%s %s has been initialized' % (self.device_name, self.device_type_value)
                self.logger.debug(msg)
                self.set_state(DevState.STANDBY, msg)
                return True
            else:
                msg = '%s %s initialization error' % (self.device_name, self.device_type_value)
                self.logger.warning(msg)
                self.set_state(DevState.FAULT, 'initialization error')
                return False
        except KeyboardInterrupt:
            raise
        except Exception as ex:
            self.init_result = ex
            log_exception(self, 'Exception initiating Tectronix oscilloscope %s', self.device_name)
            self.set_state(DevState.FAULT, 'initialization error')
            return False

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
        self.set_state(DevState.CLOSE, 'has been stopped')
        msg = '%s Tectronix oscilloscope has been deleted' % self.device_name
        self.logger.info(msg)

    @property
    def connected(self):
        if self.tec is not None:
            return self.tec.connected
        return False

    def read_horizontal_scale(self):
        try:
            v = self.tec.send_command('HORizontal:MAIn:SCAle?')
            self.hor_sc = float(v)
        except KeyboardInterrupt:
            raise
        except:
            self.log_exception()
            self.hor_sc = float('nan')
        return self.hor_sc

    def write_horizontal_scale(self, v):
        try:
            self.tec.send_command('HORizontal:MAIn:SCAle ' + str(v))
            self.hor_sc = float(v)
        except KeyboardInterrupt:
            raise
        except:
            self.log_exception()

    def read_trigger_position(self):
        try:
            v = self.tec.send_command('HORizontal:TRIGger:POSition?')
            self.trig_val = float(v)
        except KeyboardInterrupt:
            raise
        except:
            self.log_exception()
        return self.trig_val

    def write_trigger_position(self, v):
        try:
            self.tec.send_command('HORizontal:TRIGger:POSition ' + str(v))
            self.trig_val = float(v)
        except KeyboardInterrupt:
            raise
        except:
            self.log_exception()

    def read_tecronix_type(self):
        return self.device_type_value

    def read_data_ready(self):
        return self.data_ready_value

    def read_record_in_progress(self):
        return self.record_initiated

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

    def read_start_time(self):
        return self.record_start_time

    def read_stop_time(self):
        return self.record_stop_time

    def read(self):
        self.logger.debug("Reading plots")
        plots = self.tec.read_plots()
        for i in range(4):
            if i + 1 in plots:
                p = plots[i + 1]
                self.x[i] = p['x']
                self.y[i] = p['y']
            else:
                self.x[i] = empty_array
                self.y[i] = empty_array
        self.data_ready_value = True
        self.record_initiated = False

    def write_force_trigger(self, v):
        if v:
            self.send_command('TRIG FORC')

    def read_ch1_state(self):
        return bool(self.tec.get_channel_state(1))

    def write_ch1_state(self, state):
        self.tec.set_channel_state(1, bool(state))

    def read_ch1_scale(self):
        return self.tec.get_channel_scale(1)

    def write_ch1_scale(self, v):
        self.tec.set_channel_scale(1, v)

    def read_ch1_offset(self):
        return self.tec.get_channel_offset(1)

    def write_ch1_offset(self, v):
        self.tec.set_channel_offset(1, v)

    def read_chany01(self):
        return self.y[0]

    def read_chanx01(self):
        return self.x[0]

    def read_ch2_state(self):
        return self.tec.get_channel_state(2)

    def read_ch3_state(self):
        return self.tec.get_channel_state(3)

    def read_ch4_state(self):
        return self.tec.get_channel_state(4)

    def write_ch2_state(self, state):
        self.tec.set_channel_state(2, bool(state))

    def write_ch3_state(self, state):
        self.tec.set_channel_state(3, bool(state))

    def write_ch4_state(self, state):
        self.tec.set_channel_state(4, bool(state))

    def read_chany02(self):
        return self.y[1]

    def read_chany03(self):
        return self.y[2]

    def read_chany04(self):
        return self.y[3]

    def read_chanx02(self):
        return self.x[1]

    def read_chanx03(self):
        return self.x[2]

    def read_chanx04(self):
        return self.x[3]

    @command(dtype_in=None, dtype_out=bool)
    def start_recording(self):
        if self.record_initiated:
            msg = '%s Can not start - record in progress' % self.device_name
            self.logger.info(msg)
            return False
        if not self.tec.start_aq():
            self.record_initiated = False
            self.set_state(DevState.FAULT, 'Recording start fault')
            self.logger.info(self, '%s Recording start error' % self.device_name)
            return False
        self.record_initiated = True
        self.data_ready_value = False
        self.record_start_time = time.time()
        self.set_state(DevState.RUNNING, 'Recording is in progress')
        msg = '%s Recording started' % self.device_name
        self.logger.debug(msg)
        return True

    @command(dtype_in=None)
    def stop_recording(self):
        if not self.tec.stop_aq():
            # self.record_initiated = False
            # self.data_ready_value = False
            self.set_state(DevState.FAULT)
            self.set_status('Recording stop error')
            log_exception(self, '%s Recording stop error' % self.device_name, level=logging.WARNING)
            return False
        self.set_state(DevState.STANDBY)
        self.set_status('Recording has been stopped')
        self.logger.info('%s Recording has been stopped' % self.device_name)
        self.record_initiated = False

    @command(dtype_in=str, dtype_out=str)
    def send_command(self, cmd):
        return self.tec.send_command(cmd)

    def reconnect(self):
        self.tec.reconnect()
        # if self.tec.connected:
        #     self.set_state(DevState.STANDBY)
        #     self.set_status('Reconnected successfully')
        #     self.logger.info('Reconnected successfully')
        # else:
        #     self.set_state(DevState.FAULT)
        #     self.set_status('Reconnection Error')
        #     self.logger.warning('Reconnection Error')


def looping():
    # global t0
    time.sleep(0.50)
    for dev in TectronixTangoServer.device_list:
        time.sleep(0.010)
        # if time.time() - t0 > 1.0:
        #     t0 = time.time()
        #     dev.reconnect()
        if dev.record_initiated:
            try:
                if dev.tec.is_aq_finished():
                    # if dev.read_data_ready():
                    msg = '%s Recording finished, data is ready' % dev.device_name
                    dev.logger.info(msg)
                    dev.record_stop_time = time.time()
                    dev.read()
            except KeyboardInterrupt:
                raise
            except:
                log_exception(dev, '%s Reading data error' % dev.device_name, level=logging.WARNING)


if __name__ == "__main__":
    t0 = time.time()
    TectronixTangoServer.run_server(event_loop=looping)
