#      Copyright 2021. ThingsBoard
#  #
#      Licensed under the Apache License, Version 2.0 (the "License");
#      you may not use this file except in compliance with the License.
#      You may obtain a copy of the License at
#  #
#          http://www.apache.org/licenses/LICENSE-2.0
#  #
#      Unless required by applicable law or agreed to in writing, software
#      distributed under the License is distributed on an "AS IS" BASIS,
#      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#      See the License for the specific language governing permissions and
#      limitations under the License.


from pprint import pformat
from queue import Empty, Full, Queue
from random import choice
from string import ascii_lowercase
from threading import Thread
from time import sleep, time

from bluepy import __path__ as bluepy_path
from bluepy.btle import ADDR_TYPE_PUBLIC, BTLEDisconnectError, BTLEGattError, BTLEInternalError, BTLEManagementError, DefaultDelegate, Peripheral, ScanEntry, \
    Scanner, UUID, capitaliseName

from thingsboard_gateway.connectors.connector import Connector, log
from thingsboard_gateway.tb_utility.tb_loader import TBModuleLoader


class NewBLEConnector(Connector, Thread):
    DEFAULT_SERVICES_LIST = list(range(0x1800, 0x183A))

    def __init__(self, gateway, config, connector_type):
        if config.get('devices') is None:
            log.error("Devices configuration section is required!")
        super().__init__()
        self.connector_type = connector_type
        self.statistics = {'MessagesReceived': 0,
                           'MessagesSent': 0}
        self.__gateway = gateway
        self.__config = config
        self.setName(self.__config.get("name",
                                       'BLE Connector ' + ''.join(choice(ascii_lowercase) for _ in range(5))))
        self._connected = False
        self.__stopped = False
        self.check_interval_seconds = self.__config.get('checkIntervalSeconds', 10)
        self.previous_scan_period = 0
        self.rescan_time = self.__config.get('rescanIntervalSeconds', 10)
        scan_time = self.__config.get('scanTimeSeconds', 5)
        passive = self.__config.get('passiveScanMode', False)
        self.__data_workers_count = self.__config.get("dataWorkersCount", 5)
        self.__scanner_thread = Thread(target=self.__scan, name="BLE scanning thread", args=(self.rescan_time, scan_time, passive))
        self.__scanner_thread.setDaemon(True)
        converter_queue_size = self.__config.get('dataQueueSize', 1000000)
        self.__data_processing_queue = Queue(converter_queue_size)
        self.__converted_data_queue = Queue(converter_queue_size * self.__data_workers_count)
        self.__data_processing_workers = [DataProcessingWorker(self.__data_processing_queue, self.__converted_data_queue, worker_number + 1) for worker_number
                                          in range(self.__data_workers_count)]
        self.__devices = {}
        self.__available_converters = []
        self.daemon = True

    def is_connected(self):
        return self._connected

    def open(self):
        self.__stopped = False
        self.start()

    def run(self):
        self.__scanner_thread.start()
        while True:
            try:
                if self.__stopped:
                    log.debug('STOPPED')
                    break
                if self.__converted_data_queue.not_empty:
                    self.statistics['MessagesSent'] = self.statistics['MessagesSent'] + 1
                    converted_data = self.__converted_data_queue.get()
                    self.__gateway.send_to_storage(self.name, {**converted_data})
                else:
                    sleep(.001)
            except Empty:
                log.warn("Converted queue is empty!")

    def close(self):
        self.__stopped = True
        for device in self.__devices:
            try:
                if self.__devices[device].get('processor') is not None:
                    self.__devices[device]['processor'].disconnect()
            except Exception as e:
                log.exception(e)
                raise e
        for worker in self.__data_processing_workers:
            worker.stop()

    def get_name(self):
        return self.name

    def on_attributes_update(self, content):
        log.error("Not implemented yet!")

    def server_side_rpc_handler(self, content):
        log.error("Not implemented yet!")

    def add_device(self, device: ScanEntry):
        device_addr = device.addr.upper()
        for device_config in self.__config["devices"]:
            if device_config.get("MACAddress") is not None \
                    and device_config["MACAddress"].upper() == device_addr:
                if device_addr not in self.__devices:
                    self.__devices[device_addr] = {}
                    self.__devices[device_addr]["device"] = device
                    self.__devices[device_addr]["processor"] = DeviceProcessor(device, device_config, self)
                log.info("Target device found: %s", device_addr)
            else:
                log.debug('Not target device found: %s', device_addr)

    def remove_device(self, device_addr):
        if self.__devices.get(device_addr) is not None:
            removed_device = self.__devices.pop(device_addr)
            try:
                removed_device['processor'].disconnect()
            except KeyError:
                pass
            log.debug("Device %s removed.", device_addr)

    def initializing_data(self, device_addr, data):
        if device_addr in self.__devices:
            self.__devices[device_addr]["init_data"] = data

    def __scan(self, scan_period, scan_time, passive):
        scanner = Scanner().withDelegate(ScanDelegate(self))
        while not self.__stopped:
            cur_time = time()
            if cur_time - self.previous_scan_period >= scan_period:
                self.previous_scan_period = cur_time
                try:
                    scanner.scan(scan_time, passive=passive)
                except BTLEManagementError as e:
                    log.error('Cannot get access to the BLE module, please check the BLE module connection (e.g. by command \'hciconfig\').')
                    log.error('Also please notice that BLE module working only with root user.')
                    log.error('Or you can try this command:\nsudo setcap '
                              '\'cap_net_raw,cap_net_admin+eip\' %s'
                              '\n====== Attention! ====== '
                              '\nCommand above - provided access to ble devices to any user.'
                              '\n========================', str(bluepy_path[0] + '/bluepy-helper'))
                    self.__stopped = True
                    self._connected = False
                    raise e
                except BTLEDisconnectError as e:
                    log.debug(str(e))
                except Exception as e:
                    log.exception(e)
                    sleep(10)

    def add_data_task_to_queue(self, data, config, converter):
        self.statistics['MessagesReceived'] = self.statistics['MessagesReceived'] + 1
        task = (data, config, converter)
        try:
            self.__data_processing_queue.put_nowait(task)
        except Full:
            log.error("data processing queue is full!")
            self.__data_processing_queue.put(task, False, 5)


class DataProcessingWorker(Thread):
    def __init__(self, data_queue: Queue, converted_data_queue: Queue, worker_number):
        super().__init__()
        self.__data_queue = data_queue
        self.__converted_data_queue = converted_data_queue
        self.name = f"BLE data processing worker {worker_number}"
        self.__stopped = False
        self.daemon = True
        self.start()

    def run(self):
        while not self.__stopped:
            if self.__stopped:
                log.debug(f"{self.name} - stopped!")
                break
            try:
                if self.__data_queue.not_empty:
                    task = self.__data_queue.get()
                    # task is a tuple with the following format (data, config, converter)
                    try:
                        converted_data = task[2].convert(task[1], task[0])
                        if not self.__converted_data_queue.full():
                            self.__converted_data_queue.put(converted_data, True, 1)
                    except Exception as e:
                        log.error("Exception was appeared in %s thread: \n %r", self.name, e)
                else:
                    sleep(.01)
            except Empty:
                continue

    def stop(self):
        self.__stopped = True


class DeviceProcessor(Thread):
    CONFIG_SECTIONS = ['attributes', 'telemetry']
    SECTION_CONFIG_PARAMETER = 'section_config'

    def __init__(self, device: ScanEntry, device_config, connector: NewBLEConnector):
        super().__init__()
        self.__device_config = device_config
        self.__config_for_converter = {}
        self.__read_interval_seconds = device_config["checkIntervalSeconds"] if device_config.get(
            'checkIntervalSeconds') is not None else connector.check_interval_seconds
        self.__scan_entry = device
        self.__scanned_data = device.getScanData()
        self.__connector = connector
        self.uplink_converters = {}
        self.__target_characteristics = {}
        self.__found_characteristics = {}
        self.__found_descriptors = {}
        self.__prepare_config()
        self.daemon = True
        self.__device_name = self.__scan_entry.addr.upper()
        self.name = "Device %s processor" % self.__device_name
        self.__address_type = self.__device_config.get('addrType', ADDR_TYPE_PUBLIC)
        self.stopped = False
        self.peripheral = Peripheral(self.__scan_entry, self.__address_type)
        self.__previous_read_time = time() - self.__read_interval_seconds
        self.services = {}
        self.__characteristics_map = {}
        self.__default_services = []
        self.__init = True
        self.__notify_delegators = {}
        self.start()

    def __prepare_config(self):
        converters = {'BytesBLEUplinkConverter': TBModuleLoader.import_module(self.__connector.connector_type, "BytesBLEUplinkConverter")(self.__device_config)}
        target_characteristics = {}
        if self.__device_config.get('converter') is not None:
            converters[self.__device_config['converter']] = TBModuleLoader.import_module(self.__connector.connector_type,
                                                                                         self.__device_config['converter'](self.__device_config))
        for config_section in self.CONFIG_SECTIONS:
            for key_config in self.__device_config[config_section]:
                if key_config.get('characteristicUUID') is not None:
                    if key_config.get('converter') is not None:
                        converters[key_config['converter']] = TBModuleLoader.import_module(self.__connector.connector_type, key_config['converter'])(
                            self.__device_config)
                    if key_config['characteristicUUID'] not in target_characteristics:
                        target_characteristics[key_config['characteristicUUID']] = []
                    target_characteristics[key_config['characteristicUUID']].append(
                        {'converter': converters[key_config.get('converter', 'BytesBLEUplinkConverter')],
                         self.SECTION_CONFIG_PARAMETER: key_config, 'type': config_section})
        self.uplink_converters = converters
        self.__target_characteristics = target_characteristics

    def run(self):
        while not self.stopped:
            if time() - self.__previous_read_time >= self.__read_interval_seconds:
                self.__previous_read_time = time()
                try:
                    log.debug('Connecting to device: %s', self.__device_name)
                    if self.peripheral is None:
                        self.connect()
                    try:
                        log.info(self.peripheral.getState())
                    except BTLEInternalError:
                        self.connect()
                    try:
                        services = self.peripheral.getServices()
                    except BTLEDisconnectError:
                        self.connect()
                        services = self.peripheral.getServices()
                    if self.__init:
                        device_name_service = self.peripheral.getServiceByUUID(0x1800)
                        device_name_characteristic = device_name_service.getCharacteristics(0x2A00)[0]
                        device_name_from_device = str(device_name_characteristic.read())
                        device_name = self.__device_config.get('name', self.__device_config['MACAddress'])
                        if device_name_from_device != 'None':
                            device_name = device_name.replace("${deviceName}", device_name_from_device)
                        self.__config_for_converter = {
                            'deviceName': device_name,
                            'deviceType': self.__device_config.get('type', 'default')
                            }
                    for service in services:
                        if not self.services:
                            log.debug('Building device %s map, it may take a time, please wait...', self.__device_name)
                        service_uuid = str(service.uuid).upper()
                        if self.services.get(service_uuid) is None:
                            self.services[service_uuid] = {}
                            try:
                                characteristics = service.getCharacteristics()
                            except BTLEDisconnectError:
                                self.connect()
                                characteristics = service.getCharacteristics()

                            if self.__device_config.get('buildDevicesMap', False):
                                for characteristic in characteristics:
                                    descriptors = []
                                    self.connect()
                                    try:
                                        descriptors = characteristic.getDescriptors()
                                    except BTLEDisconnectError:
                                        self.connect()
                                        descriptors = characteristic.getDescriptors()
                                    except BTLEGattError as e:
                                        log.debug(e)
                                    except Exception as e:
                                        log.exception(e)
                                    characteristic_uuid = str(characteristic.uuid).upper()
                                    if self.services[service_uuid].get(
                                            characteristic_uuid) is None:
                                        self.connect()
                                        self.services[service_uuid][characteristic_uuid] = {
                                            'characteristic': characteristic,
                                            'handle': characteristic.handle,
                                            'descriptors': {}}
                                    for descriptor in descriptors:
                                        log.debug(descriptor.handle)
                                        log.debug(str(descriptor.uuid))
                                        log.debug(str(descriptor))
                                        self.services[service_uuid][characteristic_uuid]['descriptors'][descriptor.handle] = descriptor
                            else:
                                for characteristic in characteristics:
                                    characteristic_uuid = str(characteristic.uuid).upper()
                                    self.services[service_uuid][characteristic_uuid] = {
                                        'characteristic': characteristic,
                                        'handle': characteristic.handle}
                    if self.__init:
                        log.debug('New device %s - processing.', )
                        self.__init = False
                        self.__new_device_processing()
                    for interest_char in self.__target_characteristics:
                        characteristics_configs_for_processing_by_methods = {}
                        for configuration_section in self.__target_characteristics[interest_char]:
                            characteristic_uuid_from_config = configuration_section[self.SECTION_CONFIG_PARAMETER].get("characteristicUUID")
                            if characteristic_uuid_from_config is None:
                                log.error('Characteristic not found in config: %s', pformat(configuration_section))
                                continue
                            method = configuration_section[self.SECTION_CONFIG_PARAMETER].get('method')
                            if method is None:
                                log.error('Method not found in config: %s', pformat(configuration_section))
                                continue
                            characteristics_configs_for_processing_by_methods[method.upper()] = {"method": method,
                                                                                                 "characteristicUUID": characteristic_uuid_from_config}
                        for method in characteristics_configs_for_processing_by_methods:
                            data = self.__service_processing(characteristics_configs_for_processing_by_methods[method])
                            for section in self.__target_characteristics[interest_char]:
                                self.send_to_converter({**self.__config_for_converter, **section, 'clean': True}, data)
                except BTLEDisconnectError:
                    log.debug('Connection lost. Device %s', self.__device_name)
                    continue
                except Exception as e:
                    log.exception(e)

    def __new_device_processing(self):
        default_services_on_device = [service for service in self.services.keys() if
                                      int(service.split('-')[0], 16) in NewBLEConnector.DEFAULT_SERVICES_LIST]
        log.debug('Default services found on device %s :%s', self.__device_name, default_services_on_device)
        for service in default_services_on_device:
            characteristics = [char for char in self.services[service].keys() if self.services[service][char]['characteristic'].supportsRead()]
            for char in characteristics:
                read_config = {'characteristicUUID': char, 'method': 'READ'}
                try:
                    self.connect()
                    data = self.__service_processing(read_config)
                    attribute = capitaliseName(UUID(char).getCommonName())
                    read_config['key'] = attribute
                    read_config['byteFrom'] = 0
                    read_config['byteTo'] = -1
                    converter_config = {**self.__config_for_converter,
                                        "type": "attributes",
                                        "clean": True,
                                        self.SECTION_CONFIG_PARAMETER: read_config}
                    self.send_to_converter(converter_config, data)
                except Exception as e:
                    log.debug('Cannot process %s', e)
                    continue

    def __service_processing(self, characteristic_processing_conf):
        for service in self.services:
            characteristic_uuid_from_config = characteristic_processing_conf.get('characteristicUUID')
            if self.services[service].get(characteristic_uuid_from_config.upper()) is None:
                continue
            characteristic = self.services[service][characteristic_uuid_from_config]['characteristic']
            self.connect()
            data = None
            if characteristic_processing_conf.get('method', '_').upper().split()[0] == "READ":
                if characteristic.supportsRead():
                    self.connect()
                    data = characteristic.read()
                    log.debug(data)
                else:
                    log.error('This characteristic doesn\'t support "READ" method.')
            if characteristic_processing_conf.get('method', '_').upper().split()[0] == "NOTIFY":
                self.connect()
                descriptor = characteristic.getDescriptors(forUUID=0x2902)[0]
                handle = descriptor.handle
                if self.__notify_delegators is None:
                    self.__notify_delegators = {}
                if self.__notify_delegators.get(handle) is None:
                    self.__notify_delegators[handle] = {'function': self.__notify_handler}
                self.__notify_delegators[handle]['args'] = (self.__device_name, handle, self.__notify_delegators[handle].get('delegate'))
                self.__notify_delegators[handle]['delegate'] = self.__notify_delegators[handle]['function'](*self.__notify_delegators[handle]['args'])
                data = self.__notify_delegators[handle]['delegate'].data
                if data is None:
                    log.error('Cannot process characteristic: %s with config:\n%s', str(characteristic.uuid).upper(), pformat(characteristic_processing_conf))
                else:
                    log.debug('data: %s', data)
            return data

    def connect(self):
        while self.peripheral._helper is None:
            try:
                self.peripheral.connect(self.__scan_entry, self.__address_type)
            except BTLEDisconnectError as e:
                log.debug(e)
                self.__connector.previous_scan_period = time() - self.__connector.rescan_time
                self.__connector.remove_device(self.__device_name)

    def disconnect(self):
        self.stopped = True
        try:
            self.peripheral.disconnect()
        except Exception as e:
            log.debug("Error on disconnecting %s", e)

    def send_to_converter(self, config, data):
        self.__connector.add_data_task_to_queue(data, config,
                                                self.uplink_converters[config[self.SECTION_CONFIG_PARAMETER].get('converter', 'BytesBLEUplinkConverter')])

    def __notify_handler(self, device, notify_handle, delegate=None):
        class NotifyDelegate(DefaultDelegate):
            def __init__(self):
                DefaultDelegate.__init__(self)
                self.device = device
                self.data = {}

            def handleNotification(self, handle, data):
                self.data = data
                log.debug('Notification received from device %s handle: %i, data: %s', self.device, handle, data)

        if delegate is None:
            delegate = NotifyDelegate()
        self.peripheral.withDelegate(delegate)
        self.peripheral.writeCharacteristic(notify_handle, b'\x01\x00', True)
        if self.peripheral.waitForNotifications(1):
            log.debug("Data received from notification: %s", delegate.data)
        return delegate


class ScanDelegate(DefaultDelegate):
    def __init__(self, ble_connector: NewBLEConnector):
        DefaultDelegate.__init__(self)
        self.__connector = ble_connector

    def handleDiscovery(self, dev: ScanEntry, is_new_device, is_new_data):
        if is_new_device:
            self.__connector.add_device(dev)
        if is_new_data:
            self.__connector.initializing_data(dev.addr.upper(), dev.getScanData())
