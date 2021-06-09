#!/usr/bin/python

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase
import socket

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):

        def create_artpoll():
            packet = bytearray()

            # 1 ID[8]
            for char in "Art-Net\0":
                packet.append(ord(char))

            # 2 OpCode
            packet.append(0x00)
            packet.append(0x20)

            # 3 ProtVerHi
            packet.append(0x00)

            # 4 ProtVerLo
            packet.append(14)

            # 5 TalkT0Me
            packet.append(0x00)

            # 6 Priority
            packet.append(0x00)

            return(packet)


        def create_artaddress(
                net = None,
                sub_net = None,
                bind_index = 1,
                short_name = None,
                long_name = None,
                output_universe = [],
                input_universe = []
                ):
            packet = bytearray()

            # 1 ID[8]
            for char in "Art-Net\0":
                packet.append(ord(char))

            # 2 OpCode
            packet.append(0x00)
            packet.append(0x60)

            # 3 ProtVerHi
            packet.append(0x00)

            # 4 ProtVerLo
            packet.append(14)

            # 5 NetSwitch
            if net != None:
                packet.append(net|0x80)
            else:
                packet.append(0x0f)

            # 6 BindIndex
            packet.append(bind_index)

            # 7 Short Name
            for x in range(18):
                packet.append(0x00)

            # 8 Long Name
            for x in range(64):
                packet.append(0x00)

            # 9 SwIn [4]
            packet.append(0x7f)
            packet.append(0x7f)
            packet.append(0x7f)
            packet.append(0x7f)

            # 10 SwOut [4]
            for portid in range(4):
                if len(output_universe)>portid:
                    packet.append(output_universe[portid]|0x80)
                else:
                    packet.append(0x7f)

            # 11 SubSwitch
            if sub_net != None:
                packet.append(sub_net|0x80)
            else:
                packet.append(0x0f)

            # 12 SwVideo
            packet.append(0x00)
            
            # 13 Command
            packet.append(0x00)

            return(packet)

        def extract_artpollreply(message):
            data = {}

            # 1 ID[8] (8)
            # 2 Opcode[2] (10)
            # 3 IPAddress[4] (14)
            # 4 Port[2] (16)
            # 5 VersInfoH (17)
            # 6 VersInfoL (18)

            # 7 NetSwitch (19)
            data["net"]=int(message[18])

            # 8 SubSwitch (20)
            data["sub_net"]=int(message[19])

            # 9 OemHi (21)
            # 10 OemHi (22)
            # 11 Ubea Version (23)
            # 12 Status1 (24)
            
            # 13 EstaManLo (25)
            # 14 EstaManHi (26)

            data["manufacturer_id"]=int(message[24])+(int(message[25])<<8)
            
            # 15 ShortName[18] (44)
            data["short_name"]=message[26:44].decode('utf-8').split("\x00")[0]

            # 16 LongName[64] (108)
            data["long_name"]=message[44:108].decode('utf-8').split("\x00")[0]

            # 17 NodeReport[64] (172)
            # 18 NumPortsHi (173)
            # 19 NumPortsLo (174)
            # 20 PortTypes[4] (178)
            # 21 GoodInput[4] (182)
            # 22 GoodOutput[4] (186)
            # 23 SwIn[4] (190)
            data["input_universe"]=[int(message[x]) for x in range(186,190)]
            # 24 SwOut[4] (194)
            data["output_universe"]=[int(message[x]) for x in range(190,194)]
            # 25 SwVideo (195)
            # 26 SwMacro (196)
            # 27 SwRemote (197)
            # 28-30 Spare[3] (200)
            # 31 Style (201)
            # 32-37 Mac[6] (207)
            # 38 BindIp[4] (211)

            # 39 BindIndex (212)
            data["bind_index"]=int(message[211])

            # 40 Status2 (213)
            # 41 GoodOutputB[4] (217)
            # 42 Status3 (218)


            return(data)

        # print(task_vars)

        if task_vars is None:
            task_vars = dict()

        config = dict()

        if "net" in self._task.args:
            config["net"]=int(self._task.args["net"])
 
        if "sub_net" in self._task.args:
            config["sub_net"]=int(self._task.args["sub_net"])

        if "output_universe" in self._task.args:
            if type(self._task.args["output_universe"]) != list:
                config["output_universe"] = [int(self._task.args["output_universe"])]
            else:
                config["output_universe"] = [int(x) for x in self._task.args["output_universe"]]

        address = task_vars["ansible_host"]
        print(config)
        
        #get current settings

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 6454))
        sock.sendto(create_artpoll(),(task_vars["ansible_host"], 6454))
        data = sock.recvfrom(1024)
        settings = extract_artpollreply(data[0])

        toset = dict()

        for item in config:
            # for arrays check each item
            if type(config[item])==list:
                different=0
                for x in range(len(config[item])):
                    if settings[item][x]!=config[item][x]:
                        different=1
                if different:
                    toset[item]=config[item]
            else:
                if settings[item]!=config[item]:
                    toset[item]=config[item]

        if len(toset) == 0:
            return ({"changed":False})


        sock.sendto(create_artaddress(**toset),(task_vars["ansible_host"], 6454))
        data = sock.recvfrom(1024)
        settings = extract_artpollreply(data[0])

        failed = 0
        msg = ""
        for item in toset:
            # for arrays check each item
            if type(toset[item])==list:
                for x in range(len(toset[item])):
                    if settings[item][x]!=toset[item][x]:
                        msg += "Missmatch on {}-{} {}!={}\n".format(item,x,settings[item][x],toset[item][x])
                        failed += 1
            else:
                if settings[item]!=toset[item]:
                    msg += "Missmatch on {} {}!={}\n".format(item,settings[item],toset[item])
                    failed += 1
        
        if failed:
            return({"failed":True,"msg":msg})
        
        return({"changed":True})
