import json
import os 
import sys
import argparse
import struct
import math

def receive_args(): 
    parser = argparse.ArgumentParser()
    parser.description = argparse.ArgumentParser(
        description='configuration tool')
    parser.add_argument("-f", type=str, help="bin file path")
    parser.add_argument("-s", type=str, help="setting file path")
    parser.add_argument("-t", type=str, help="config type: user or factory")
    return parser.parse_args()


def calc_crc(payload):
    crc = 0x1D0F
    for bytedata in payload:
        crc = crc ^ (bytedata << 8)
        i = 0
        while i < 8:
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            i += 1
        crc = crc & 0xffff

    crc_msb = ((crc >> 8) & 0xFF)
    crc_lsb = (crc & 0xFF)
    return [crc_msb, crc_lsb]

class create_user_config_file:
    def __init__(self, bin_file, json_setting):
        self.setting = json_setting
        self.bin_file = bin_file
        self.fs_bin = open(self.bin_file, 'wb')
        with open(json_setting) as json_data:
            self.config = json.load(json_data)
        self.packet_format = None
        self.value = list()
        self.crc_list = list()
        self.crc_len = 2
        self.all_len_list = list()
        self.len_len = 2
        self.bin_data = list()
    def get_format(self):
        length = 0
        cur_len = 0
        data_len = 0
        pack_fmt = '@'    
        for ele in self.config['user_config']:
            if ele['type'] == 'float':
                pack_fmt += 'f'
                length += 4
                data_len = 4
            elif ele['type'] == 'uint32':
                pack_fmt += 'I'
                length += 4
                data_len = 4
            elif ele['type'] == 'int32':
                pack_fmt += 'i'
                length += 4
                data_len = 4
            elif ele['type'] == 'int16':
                pack_fmt += 'h'
                length += 2
                data_len = 2
            elif ele['type'] == 'uint16':
                pack_fmt += 'H'
                length += 2
                data_len = 2
            elif ele['type'] == 'double':
                pack_fmt += 'd'
                length += 8
                data_len = 8
            elif ele['type'] == 'int64':
                pack_fmt += 'q'
                length += 8
                data_len = 8
            elif ele['type'] == 'uint64':
                pack_fmt += 'Q'
                length += 8
                data_len = 8
            elif ele['type'] == 'char':
                pack_fmt += 'c'
                length += 1
                data_len = 1
            elif ele['type'] == 'uchar':
                pack_fmt += 'B'
                length += 1
                data_len = 1
            elif ele['type'] == 'uint8':
                pack_fmt += 'B'
                length += 1
                data_len = 1
            if cur_len % data_len != 0:
                cur_len = math.ceil(cur_len/data_len) * data_len
            #print(cur_len, ele['type'])
            cur_len+= data_len
        len_fmt = '{0}B'.format(length)
        self.packet_format = pack_fmt
        print(pack_fmt, cur_len + self.crc_len + self.len_len)
        all_len = cur_len + self.crc_len + self.len_len

        if ( (all_len % 4) != 0 ):
            all_len = math.ceil(all_len / 4) * 4
            
        self.all_len = all_len
        all_len_msb = ((all_len >> 8) & 0xFF)
        all_len_lsb = (all_len & 0xFF)        
        self.all_len_list = [all_len_lsb, all_len_msb]
        
    def get_value(self):
        length = 0
        pack_fmt = '<'    
        for ele in self.config['user_config']:
            self.value.append(ele['value'])

    def get_bin_data(self):
        config_byte = struct.pack(self.packet_format, *self.value)
        self.bin_data = list(config_byte)
        if (len(self.bin_data) % 4) != 0:
            fill_len = 4 - (len(self.bin_data) % 4 )
            fill_data = [0] * fill_len
            self.bin_data = self.bin_data + fill_data
        
    def get_crc(self, data):
        self.crc_list = calc_crc(data)
        
    def get_bin(self):
        self.fs_bin.write(bytes(self.bin_data))
        self.fs_bin.close()
        
    def get_configuration_bin(self):
        self.get_format()
        self.get_value()
        self.get_bin_data()
        
        data_to_crc = self.all_len_list + self.bin_data 
        data_to_crc_len = len(data_to_crc)
        data_to_crc = data_to_crc
        self.get_crc(data_to_crc)
        self.bin_data = self.crc_list + data_to_crc
        self.get_bin()

class create_factory_config_file:
    def __init__(self, bin_file, json_setting):
        self.setting = json_setting
        self.bin_file = bin_file
        self.fs_bin = open(self.bin_file, 'wb')
        with open(json_setting) as json_data:
            self.config = json.load(json_data)
        self.packet_format = None
        self.value = list()
        self.crc_list = list()
        self.crc_len = 2
        self.all_len_list = list()
        self.len_len = 2
        self.bin_data = list()
    def get_format(self):
        length = 0
        pack_fmt = '<'    
        for ele in self.config['config']:
            len_factor = ele['len']
            if ele['type'] == 'float':
                pack_fmt += 'f'*len_factor
                length += 4*len_factor
            elif ele['type'] == 'int16':
                pack_fmt += 'h'*len_factor
                length += 2*len_factor
            elif ele['type'] == 'uint16':
                pack_fmt += 'H'*len_factor
                length += 2*len_factor
        len_fmt = '{0}B'.format(length)
        self.packet_format = pack_fmt
        all_len = length + self.crc_len + self.len_len
        all_len_msb = ((all_len >> 8) & 0xFF)
        all_len_lsb = (all_len & 0xFF)        
        self.all_len_list = [all_len_lsb, all_len_msb]
        
    def get_value(self):
        length = 0
        pack_fmt = '<'    
        for ele in self.config['config']:
            if isinstance(ele['value'], list) == True:
                for list_ele in ele['value']:
                    self.value.append(list_ele)
            else:
                self.value.append(ele['value'])

    def get_bin_data(self):
        config_byte = struct.pack(self.packet_format, *self.value)
        self.bin_data = list(config_byte)
        
    def get_crc(self, data):
        self.crc_list = calc_crc(data)
        
    def get_bin(self):
        self.fs_bin.write(bytes(self.bin_data))
        self.fs_bin.close()
        
    def get_configuration_bin(self):
        self.get_format()
        self.get_value()
        self.get_bin_data()
        self.get_bin()



class config_tool:
    def create(name, bin_file, json_setting):
        if name == 'user':
            return create_user_config_file(bin_file, json_setting)
        elif name == 'factory':
            return create_factory_config_file(bin_file, json_setting)
            
            
if __name__ == '__main__':
    args = receive_args()
    tool = config_tool.create(args.t, args.f, args.s)
    tool.get_configuration_bin()
        
    