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

message = dict()

def findchain(myactivka, m, hostname = False):
    '''
    Function get object Activka and mac address and return
    name of switch, port, IP and hostname if possible where
    host with that mac 
    '''
    global message
    end = []
    i = 0
    mac_to_find = m[1]
    correct_ip = m[0]
    if hostname:
        print(f'DEBUG hostname = {hostname}\nmessage[20] = {message[20]}')
        return_text = [message[20].format(hostname, correct_ip, mac_to_find, m[3], m[2])]
    else:
        return_text = [message[21].format(correct_ip, mac_to_find, m[3], m[2])]
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
        print(message[22].format(sw, port[0]))
        return_text.append(message[22].format(sw, port[0]))
        if not port[1]:
            next_neighbor = myactivka.getinfo(sw, 'neighbor_by_port', port[0])
            #если за портом много устройств но ни по CDP ни по LLDP соседа не получаем, значит там “тупой” неуправляемый коммутатор, останавливаемся и сообщаем об этом
            if not next_neighbor :
                return_text.append(message[23].format(sw, port[0]))
                break
            else:
                sw = next_neighbor 
        else:
            return_text.append(message[24].format(sw, port[0]))
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
    global message
    return_text = []
    routers = [rt for rt in devices if myactivka.levels[rt] == 'R' or myactivka.levels[rt] == 'L3']
    for rt in routers:
        m = find_router_to_start(myactivka, mac_to_find, is_mac = True, router = rt)
        #print(f'DEBUG m = {m}')
        if m:
            hostname = nslookup(m[0], reverse = False)
            out = findchain(myactivka, m, hostname)
            if out[-1]:
                return out[0]
    switches = [sw for sw in devices if myactivka.levels[sw] == 'L2' or myactivka.levels[sw] == 'L3']
    print(message[16].format(mac_to_find))
    for sw in switches:
        print(message[17].format(sw))
        mac_to_find = convert_mac(mac_to_find, myactivka.choose(sw, withoutname = True)['device_type'])
        port = myactivka.getinfo(sw, 'mac_address_table',  mac_to_find)
        if port:
            return_text.append(message[18].format(mac_to_find, sw, port[0]))
            print(return_text[0])
            return return_text
    return_text.append(message[19].format(mac_to_find))
    print(return_text[0])
    return return_text       



def find_router_to_start(myactivka, ip, is_mac = False, router = None):
    '''
    Function get IP (or MAC if is_mac=True) address and lookup routers as start point 
    and return list(IP,MAC, port_where_was _found, name_of_router)
    '''
    #ищу 3-й октет адреса и по нему из файла networks_byip.yaml получаю имя роутера (стартовой точки поиска)
    global message
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
        print_string = message[14].format(ip, routerstart)
    else:
        print_string = message[15].format(routerstart, ip )
     
    if not out:
        print(print_string)
        return False
    #в возвращаемый список [IP, MAC, PORT] добавляю еще имя роутера,  find_mac_by_ip() сделал универсальной, нот имя роутера мне дальше необходимо
    output = out[0]
    output.append(routerstart)
    return output
    
    
    


def ip_routine(myactivka,ip):
    global message
    if not re.match(r'[,|\.]', ip):
        ipreal = nslookup(ip)
        if not ipreal:
            print(message[10].format(ip))
            quit()
        else:
            correct_ip = ipreal
        hostname = ip
    else:
        #а вдруг команду old_fh.exe вызвали из буфера а адрес ввели при русской раскладке и вместо “.” у вас “,” или просто ошиблись - проверяем и возвращаем правильный IP
        correct_ip = is_ip_correct(ip)
        if not correct_ip:
            print(message[11])
            quit()
        #а если ввели IP не плохо бы узнать DNS имя
        hostname = nslookup(correct_ip, reverse = False)
        if not hostname:
            hostname = message[12]
    #по IP получаем список  m = [IP, MAC, порт на котором светится, имя активки]
    m = find_router_to_start(myactivka, correct_ip)
    if not m:
        print(message[13])
        quit()
    out = findchain(myactivka, m, hostname)
    return out

    
def mac_routine(myactivka,ip):
    global message
    segment_list = list(myactivka.segment.values())
    sl = sorted(set(segment_list))
    sl_len = [x for x in range(0, len(sl))]
    print(message[7])
    for a, b in zip(sl_len,sl):
        print(a,b)
    seg = input(message[8])
    seg_name = sl[int(seg)]
    seg_devices = [dev for dev, value in myactivka.segment.items() if value == seg_name ]
    out = findbymac(myactivka, ip, seg_devices)
    if not out:
        print(message[9].format(seg_name))
        return False
    else:
        return out[0]



if __name__ == "__main__":
    
    file = myini.localpath + 'messages_' + myini.language + '.yaml'
    with open(file, encoding='utf8') as f:
        message = yaml.safe_load(f)
    parser = argparse.ArgumentParser(description=message[2])
    parser.add_argument( dest="ip", help = message[3])
    parser.add_argument('-s', dest='seg', default='RPB', help = message[4])
    parser.add_argument("-r", dest="repeat", default=False, type=bool, help = message[5])
    parser.add_argument("-f", dest="file_to_save", help = message[6])
    args = parser.parse_args()

    
    #если ввели fh без аргументов попросит ввести адрес или имя хоста

    try:
        ip = args.ip
    except IndexError:
        ip = ''
        while not ip:
            ip = input(message[0])

    print(message[1])
    myactivka = Activka('activka_byname.yaml', 'activka_byip.yaml')
    is_mac = convert_mac(ip,'cisco_ios')
    repeat_out = []
    while True:
        if not is_mac:
            out = ip_routine(myactivka, ip)
            repeat_out.append(out)
        else:
            out = mac_routine(myactivka,is_mac)
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
            ip = input(message[0])
            if ip == 'q':
                if args.file_to_save:
                    repeat_out = '\n'.join(repeat_out[0])                       
                    with open(args.file_to_save, 'w') as f: 
                        f.writelines(repeat_out)            
                    break
            is_mac = convert_mac(ip,'cisco_ios')                                       

