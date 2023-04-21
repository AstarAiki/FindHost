#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re, yaml, argparse
from net_func import (
    Activka,
    port_name_normalize,
    convert_mac,
    is_ip_correct,
    nslookup,
    myini,
    )



def findchain(myactivka, m, hostname = False):
    '''
    Function get object Activka and mac address and return
    name of switch, port, IP and hostname if possible where
    host with that mac 
    '''
    end = []
    i = 0
    mac_to_find = m[1]
    correct_ip = m[0]
    if hostname:
        return_text = [f'host {hostname}, ip address: {correct_ip}, mac address: {mac_to_find}\search starting point: {m[3]} go through port: {m[2]}']
    else:
        return_text = [f'ip address: {correct_ip}, mac address: {mac_to_find}\search starting point: {m[3]} go through port: {m[2]}']
    print(return_text[0])
    #теперь нам необходимо узнать  тип активки ‘R’ - маршрутизатор ‘L3’ - L3 коммутатор или ‘CH’ checkpoint это необходимо чтобы понять где начинать поиск по таблице MAC адресов (на роутере бессмысленно, надо добраться до первого коммутатора в цепочке
    if not myactivka.levels[m[3]] == 'CH':
        #проверяем, не светится ли искомый нами MAC на Ether-Channel интерфейсе, если да, нам необходимо получить имена интерфейсов в него входящих, так как и cdp и lldp оперируют физическими интерфейсами
        match = re.search(r'(Eth-Trunk|Po)(\d+)',m[2])
        if match:
            m[2] = str(myactivka.getinfo(m[3], 'ethchannel_member', match.group(2))[0][0][0])
            m[2] = port_name_normalize(m[2])
            #если стартовая точка - роутер, ищем первый на пути коммутатор, если L3 коммутатор - начнем поиск с него
        if myactivka.levels[m[3]] == 'R':
            sw = myactivka.getinfo(m[3], 'neighbor_by_port', m[2])
        else:
            sw = m[3]
    else:
        if m[3] == 'ChPSever-HA':
            sw = 'swSever2960-1'
        elif m[3] == 'ChPGDN-HA':
            sw = 'swGDN2960-1'
            #и в бесконечном цикле идем по цепочке коммутаторов, пока не найдем последний, к которому подключен хост

    while True:
        match = re.search(r'([-a-zA-Z0-9]+)(\.\S+)',sw)
        if match:
            sw = match.group(1)
        end.append(sw)
        i += 1
        mac_to_find = convert_mac(mac_to_find, myactivka.choose(sw, withoutname = True)['device_type'])
        port = myactivka.getinfo(sw, 'mac_address_table',  mac_to_find)
        #port = [имя порта, Status] где Status = True если к порту подключен 1 MAC или если больше то это MAC IP телефона и Status = False если дальше светится много MACов
        print(f'next device: {sw} port: {port[0]}')
        return_text.append(f'next device: {sw} port: {port[0]}')
        if not port[1]:
            next_neighbor = myactivka.getinfo(sw, 'neighbor_by_port', port[0])
            #если за портом много устройств но ни по CDP ни по LLDP соседа не получаем, значит там “тупой” неуправляемый коммутатор, останавливаемся и сообщаем об этом
            if not next_neighbor :
                return_text.append(f'connected to an unmanaged switch in switch: {sw}, port: {port[0]}')
                break
            else:
                sw = next_neighbor 
        else:
            return_text.append(f'connected to the switch: {sw}, port: {port[0]}')
            break
    print(return_text[-1])
    out = return_text + end
    return out

    #print(f'Время выполнения заняло: {time.time()-timestart}')

def findbymac(myactivka, mac_to_find, devices):
    '''
    Function get object Activka, mac address to find, segment of network
    and return name of switch, port, IP and hostname if possible where
    host with that mac 
    '''
    return_text = []
    routers = [rt for rt in devices if myactivka.levels[rt] == 'R' or myactivka.levels[rt] == 'L3']
    for rt in routers:
        m = find_router_to_start(myactivka, mac_to_find, is_mac = True, router = rt)
        #print(f'DEBUG m = {m}')
        if m:
            out = findchain(myactivka, m)
            if out[-1]:
                return out[0]
    switches = [sw for sw in devices if myactivka.levels[sw] == 'L2' or myactivka.levels[sw] == 'L3']
    print(f'the device with the MAC address {mac_to_find} apparently does not have an IP address')
    for sw in switches:
        print(f' Starting to search on the switch {sw}')
        mac_to_find = convert_mac(mac_to_find, myactivka.choose(sw, withoutname = True)['device_type'])
        port = myactivka.getinfo(sw, 'mac_address_table',  mac_to_find)
        if port:
            return_text.append(f'a device with a MAC address: {mac_to_find} either does not have an IP address or its address is not routed\n is included in the switch {sw} to the port: {port[0]}')
            print(return_text[0])
            return return_text
    return_text.append(f'device with MAC address: {mac_to_find} not found in this network segment')
    print(return_text[0])
    return return_text       



def find_router_to_start(myactivka, ip, is_mac = False, router = None):
    '''
    Function get IP (or MAC if is_mac=True) address and lookup routers as start point 
    and return list(IP,MAC, port_where_was _found, name_of_router)
    '''
    #ищу 3-й октет адреса и по нему из файла networks_byip.yaml получаю имя роутера (стартовой точки поиска)
    if not is_mac:
        ia = re.compile(r'(?P<OCT1>\d+)\.(?P<OCT2>\d+)\.(?P<OCT3>\d+)\.(?P<OCT4>\d+)', re.ASCII)
        m = ia.search(ip)
        oct3 = m.group('OCT3')
        with open(myini.localpath + 'networks_byip.yaml') as f:
            nbi = yaml.safe_load(f)
        if not oct3 in nbi.keys():
            return False
        else:
            routerstart = nbi[oct3]
    #и через ARP таблицу ищу MAC для этого IP
    else:
        routerstart = router
    out = myactivka.getinfo(routerstart, 'arp', ip)
    if is_mac:
        print_string = f'looking for a host with a MAC address {ip} on the router {routerstart}'
    else:
        print_string = f' Or for some reason I can\'t connect to the starting point of the search {routerstart}\or most likely the host {ip} is not online'
     
    if not out:
        print(print_string)
        return False
    #в возвращаемый список [IP, MAC, PORT] добавляю еще имя роутера,  find_mac_by_ip() сделал универсальной, нот имя роутера мне дальше необходимо
    output = out[0]
    output.append(routerstart)
    return output
    
    
    


def ip_routine(myactivka,ip):
    if not re.match(r'[,|\.]', ip):
        ipreal = nslookup(ip)
        if not ipreal:
            print(f'host {ip} won\'t resolve, I can\'t find it')
            quit()
        else:
            correct_ip = ipreal
        hostname = ip
    else:
        #а вдруг команду old_fh.exe вызвали из буфера а адрес ввели при русской раскладке и вместо “.” у вас “,” или просто ошиблись - проверяем и возвращаем правильный IP
        correct_ip = is_ip_correct(ip)
        if not correct_ip:
            print('You entered the wrong IP address, check and repeat')
            quit()
        #а если ввели IP не плохо бы узнать DNS имя
        hostname = nslookup(correct_ip, reverse = False)
        if not hostname:
            hostname = '(missing in DNS)'
    #по IP получаем список  m = [IP, MAC, порт на котором светится, имя активки]
    m = find_router_to_start(myactivka, correct_ip)
    if not m:
        print('Maybe it\'s a p2p network address between activka, or an address outside our network')
        quit()
    out = findchain(myactivka, m, hostname)
    return out

    
def mac_routine(myactivka,ip):
    global progmessages
    segment_list = list(myactivka.segment.values())
    sl = list(set(segment_list))
    sl_len = [x for x in range(0, len(sl))]
    print(f'Specify in which segment this MAC address is located')
    for a, b in zip(sl_len,sl):
        print(a,b)
    seg = input('Select a network segment from the list: ')
    seg_name = sl[int(seg)]
    seg_devices = [dev for dev, value in myactivka.segment.items() if value == seg_name ]
    out = findbymac(myactivka, ip, seg_devices)
    if not out:
        print('this MAC address was not found in the network segment {seg_name}')
        return False
    else:
        return out[0]



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Find host by ip/mac/name')
    parser.add_argument( dest="ip", help = 'IP or MAC address of host or hostname without domain name')
    parser.add_argument('-s', dest='seg', default='RPB', help = 'Network segment by name from active_by name.yaml , to stop enter "q", used only when specifying the MAC address')
    parser.add_argument("-r", dest="repeat", default=False, type=bool, help = 'repeat for many addresses, programm will ask next, must be set to True')
    parser.add_argument("-f", dest="file_to_save", help = 'save output to file')
    args = parser.parse_args()

    
    #если ввели fh без аргументов попросит ввести адрес или имя хоста

    try:
        ip = args.ip
    except IndexError:
        ip = ''
        while not ip:
            ip = input('Input address: ')


    myactivka = Activka('activka_byname.yaml', 'activka_byip.yaml')
    is_mac = convert_mac(ip,'cisco_ios')
    repeat_out = []
    while True:
        if not is_mac:
            out = ip_routine(myactivka, ip)
            repeat_out.append(out)
        else:
            out = mac_routine(myactivka,ip)
            repeat_out.append(out)
        if not args.repeat:
            if args.file_to_save:
                repeat_out = '\n'.join(repeat_out[0])
                with open(args.file_to_save, 'w') as f:
                    f.writelines(repeat_out)
                break
            else:
                break
        else:
            ip = input('Input address: ')
            if ip == 'q':
                if args.file_to_save:
                    repeat_out = '\n'.join(repeat_out[0])                       
                    with open(args.file_to_save, 'w') as f: 
                        f.writelines(repeat_out)            
                    break
            is_mac = convert_mac(ip,'cisco_ios')                                       

