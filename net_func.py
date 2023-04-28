import os, yaml, textfsm, logging, re, time

#logging.basicConfig(filename='d:/network/net_func.log',format='%(asctime)s : %(level)s - %(message)s', datefmt='%Y-%B-%d %H:%M:%S', level=logging.WARNING)



def find_in_env_path(file_name, folders):
    for folder in folders:
        for element in os.scandir(folder):
            if element.is_file():
                if element.name == file_name:
                    return folder
    else:
        return False

class StartOptions:
    
    def __init__(self, fi):
        from os import  path
        import psutil
        if not path.dirname(fi):
            p = psutil.Process().exe()
            path_to_ini = path.abspath(path.join(path.dirname(p), fi))
        else:
            path_to_ini = fi
        with open(path_to_ini, encoding="utf8") as f:
            d = yaml.safe_load(f)
        for key in d.keys():
            setattr(self, key, d[key])

myini = StartOptions('fh.ini')    


def send_config_by_one(device, commands, log=False):
    '''
    The function connects via SSH (using net mikko) to ONE device and performs
     a list of commands in configuration mode based on the arguments passed.
    '''
    from netmiko import (
    ConnectHandler,
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
    )

    if type(commands) == str:
        commands = [commands]
    good = {}
    failed = {}
    errors_str = re.compile(r'Invalid input detected|Incomplete command|Ambiguous command|Unrecognized command')
    try:
        if log:
            print('Подключаюсь к {}...'.format(device['host']))
        with ConnectHandler(**device) as ssh:
            ssh.enable()
            for command in commands:
                result = ssh.send_config_set(command)
                if not errors_str.search(result):
                    good[command] = result
                else:
                    logging.warning(f"Комманда {command} выполнилась с ошибкой: {errors_str.search(result).group()} на устройстве {device['host']}")
                    failed[command] = result
            out = (good,failed)
            return out
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
        logging.warning(error)

def send_config_commands(device, commands, log=True):
    '''
    The function connects via SSH (using netmikko) to ONE device and performs 
    a list of commands in configuration mode based on the arguments passed.
    '''
    import time
    from netmiko import (
    ConnectHandler,
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
    )

    if type(commands) == str:
        commands = [commands]
    try:
        if log:
            print(f"Подключаюсь к {device['ip']}...")
        with ConnectHandler(**device) as ssh:
            ssh.enable()
            result = ssh.send_config_set(commands, delay_factor = 20)
            time.sleep(10)
            result += ssh.send_command_timing('write')
            return result
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
        logging.warning(error)



def send_show_command(device, commands, log=True):
    '''
   The function connects via SSH (using netmiko) to ONE device
    and executes the specified command.
    Function Parameters:
    * device - dictionary with device connection parameters
    * command - the command to be executed
    The function returns a string with the output of the command.
    '''
    from netmiko import (
    ConnectHandler,
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
    )
    from datetime import datetime
    if log:
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        logging.basicConfig(
        filename = myini.localpath + 'net_func.log',
        format = '%(threadName)s %(name)s %(levelname)s: %(message)s',
        level=logging.INFO)
        connect_string = '===> {} Подключаюсь к {}'
        not_connect_string = '===> {}  Не могу подключиться к {}'
        logging.info(connect_string.format(datetime.now().time(), device['ip']))
    try:
        if ping_one_ip(device['ip']) == 0:
            with ConnectHandler(**device) as ssh:
                ssh.enable()
                result = ssh.send_command(commands)
                return result
        else:
            if log:
                logging.info(not_connect_string.format(datetime.now().time(),device['ip']))
            return False
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
        if log:
            logging.warning(error)

def ping_one_ip(ip_address):
    '''
    Function get one ip address and return 0 if all is o'key or else error code
    '''

    import subprocess as sp
    if os.name == 'nt':
        reply = sp.run(['ping','-n','3',ip_address], stdout = sp.DEVNULL)
    else:
        reply = sp.run(['ping','-c','3','-n',ip_address], stdout = sp.DEVNULL)
    
    return reply.returncode

def templatizator(*args, special = False):
    '''
    The function receives the output of a command from network equipment and or 
    1. the standard command itself in the form of an abbreviation for which 
    there is a textFSM template or 2. any command, 
    then a second positional parameter is needed - the template file name 
    and the special variable must be set to True
    and returns a list of lists obtained using the corresponding textfsm template
    '''
    if not special:
        if args[2] == 'cisco_ios':
            tf = myini.templpath + 'cisco_' + args[1] + '.template'
        elif args[2] == 'huawei':
            tf = myini.templpath + 'huawei_' + args[1] + '.template'
        elif args[2] == 'checkpoint_gaia':
            tf = myini.templpath + 'checkpoint_' + args[1] + '.template'
        elif args[2] == 'nt':
            tf = myini.templpath + 'nt_' + args[1] + '.template'
        elif args[2] == 'posix':
            tf = myini.templpath + 'posix_' + args[1] + '.template'
    else:
        tf = myini.templpath + args[1]
    with open(tf) as tmpl:
        fsm = textfsm.TextFSM(tmpl)
        result = fsm.ParseText(args[0])
    return result



def port_name_normalize(port):
    '''
    The function gets the port name and if it is abbreviated, returns the full name. 
    It is actually necessary to bypass the Huawei hardware property to return 
    the interface name as GE and require the input of Gi
    '''
    portnorm = []
    m = re.search(r'(Eth-Trunk|Po|GE|Gi|XGE|Fa)(\S+)', port)
    if m:
        if m.group(1) == 'Eth-Trunk' or m.group(1) == 'Po':
            portnorm = f'{m.group(0)}'
            return portnorm
        else:
            if m.group(1)[0] == 'G':
                longname = 'GigabitEthernet'
            if m.group(1)[0] == 'X':
                longname = 'XGigabitEthernet'
            if m.group(1)[0] == 'F':
                longname = 'FastEthernet'
            portnorm = f'{longname}{m.group(2)}'
            return portnorm

def get_port_by_mac(device, mac):
    '''
    The function gets a device dictionary to connect to and a MAC to search on which port it lights up
    returns a list of [Port,Status] where Status is the destination port (True) 
    or there is another switch behind it (False)
    '''
    status = True

    commands = {'cisco_ios':f'show mac address-table | in {mac}','huawei':f'display mac-address | in {mac}'}
    command = commands[device['device_type']]
    todo = send_show_command(device, command)
    out = templatizator(todo, 'mac_address_table', device['device_type'])[0]
    out[2] = port_name_normalize(out[2])
    commands = {'cisco_ios':f'show mac address-table int {out[2]}','huawei':f'display mac-address {out[2]}'}
    command = commands[device['device_type']]
    todo = send_show_command(device, command)
    outwhole = templatizator(todo, 'mac_address_table', device['device_type'])
    if len(outwhole) > 2:
        if len(outwhole) == 3: #если компютер включен через IP телефон то светится 2 MAC в 2-х VLAN
            for mac in myini.phone_mac:#у нас все телефоны имеют MAC начинающийся на 805e но ведь могут появиться и другие
                if mac in outwhole[2][0]:
                    return [out[2], status]
        else:
            status = False
    return [out[2], status]

def convert_mac(mac,device_type):
    '''
    The function gets the MAC address string in any type and the device_type (like in netmiko).
    Returns the MAC string in the form accepted on this hardware
    MAC can be in the form of 4 by 3 or 6 by 2 separators are also different
    '''
    delimeters = {'cisco_ios':'.','huawei':'-', 'win':':','catos':'-'}
    trudelim = delimeters[device_type]
    p4=re.compile(r'(?P<oct1>[0-9a-fA-F]{4})[-|.|:](?P<oct2>[0-9a-fA-F]{4})[-|.|:](?P<oct3>[0-9a-fA-F]{4})', re.ASCII)
    p6=re.compile(r'(?P<oct1>[0-9a-fA-F]{2})[-|.|:](?P<oct2>[0-9a-fA-F]{2})[-|.|:](?P<oct3>[0-9a-fA-F]{2})[-|.|:](?P<oct4>[0-9a-fA-F]{2})[-|.|:](?P<oct5>[0-9a-fA-F]{2})[-|.|:](?P<oct6>[0-9a-fA-F]{2})', re.ASCII)
    m = p4.search(mac)
    if m:
        if device_type == 'cisco_ios' or device_type == 'huawei':
            trumac = f'{m.group(1)}{trudelim}{m.group(2)}{trudelim}{m.group(3)}'
        else:
            trumac = f'{m.group(1)[0:2]}{trudelim}{m.group(1)[2:4]}{trudelim}{m.group(2)[0:2]}{trudelim}{m.group(2)[2:4]}{trudelim}{m.group(3)[0:2]}{trudelim}{m.group(3)[2:4]}'
    else:
        m = p6.search(mac)
        if m:
            if device_type == 'cisco_ios' or device_type == 'huawei':
                trumac = f'{m.group(1)}{m.group(2)}{trudelim}{m.group(3)}{m.group(4)}{trudelim}{m.group(5)}{m.group(6)}'
            else:
                trumac = f'{m.group(1)}{trudelim}{m.group(2)}{trudelim}{m.group(3)}{trudelim}{m.group(4)}{trudelim}{m.group(5)}{trudelim}{m.group(6)}'
        else:
            return False
    return trumac



def is_ip_correct(ip):
    '''
    The function receives the IP address string and, if it is correct, 
    returns it if the Russian layout is enabled
    and instead of dots, commas, changes and returns the correct address
    if the address is incorrect, returns False
    '''
    if re.search(r'^(?:(?:^|\.)(?:2(?:5[0-5]|[0-4]\d)|1?\d?\d)){4}$',ip):
        return ip
    else:
        if re.search(r'^(?:(?:^|\,)(?:2(?:5[0-5]|[0-4]\d)|1?\d?\d)){4}$',ip):
            return re.sub(',','.',ip)
        else:
            return False





def nslookup(hostname, reverse = True):
    '''
    The function gets the host name and returns a list of its IP addresses. 
    Or vice versa (reverse = True) finds the DNS name by IP address
    '''
    import socket, subprocess
    
    if reverse:
        try:
            ip = socket.gethostbyname(hostname)
        except:
            ip = False 
        return ip
    else:
        if os.name == 'nt':
            code = 'cp1251'
        elif os.name == 'posix':
            code = 'utf_8'
        todo = subprocess.run(['nslookup', hostname], stdout = subprocess.PIPE, stderr = subprocess.PIPE, encoding = code)
        name = templatizator(todo.stdout, 'nslookup', os.name)
        if not name:
            return False
        return name[0][0]



def del_exeption(config):
    to_lookup = ['ntp clock-period']
    for i, line in enumerate(config):
        for tl in to_lookup:
            if tl in line:
                config.pop(i)
    return config


def check_exeption(curr_config, last_backup):
    if del_exeption(curr_config) == del_exeption(last_backup):
        return True
    else:
        return False


class TimeMeasure:
    '''
    The class allows you to measure the execution time of a program or subroutine
    '''
    def __init__(self):
        pass
    def __enter__(self):
        self.start = time.time()
    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f'Время выполнения программы заняло: {time.time() - self.start}')




class Activka:
    '''
    The class represents all our network devices - routers and switches
    '''
    def __init__(self, byname, byip):
        username = 'starkova'
        userpoint = 'astar'  
        password = 'Mitlun@K123'  
        with open(myini.localpath + byname) as fyaml:
            wholedict = yaml.safe_load(fyaml)
        with open(myini.localpath + byip) as fyaml:
            allip = yaml.safe_load(fyaml)
        r_and_s ={}
        devices = list(wholedict.keys())
        devices.remove('LEVEL')
        devices.remove('SEGMENT')
        self.devices = devices
        self.levels = wholedict['LEVEL']
        self.segment = wholedict['SEGMENT']
        del wholedict['LEVEL']
        del wholedict['SEGMENT']
        for d in devices:
            if not self.levels[d] == 'CH':
                wholedict[d]['username'] = username
                wholedict[d]['password'] = password
                r_and_s[d] = wholedict[d]
            else:
                wholedict[d]['username'] = userpoint
                wholedict[d]['password'] = password
        self.wholedict = wholedict
        self.r_and_s = r_and_s
        self.routerbyip = allip
    
    def __repr__(self):
        return(f'{self.__class__.__name__}({self.__class__.__doc__})')
    
    def choose(self, *args, withoutname = False):
        '''
        Function return dictionary for connection to device by netmiko if
        withoutname=True or 
        dictionary of dicrionary like {device_name:{dictionary for conect}}
        '''
        out = {}
        if withoutname:
            for d in args:
                out.update(self.wholedict[d])
        else:
            for d in args:
                out[d] = self.wholedict[d]
        return out

    def filter(self, device_type = None, levels = None, segment = None):
        '''
        Function return dictionary of dicrionary like {
        device_name:{dictionary for conect},} filtered from wholedict by
        parameters device_type or levels
        '''
        cycle1 = {}
        cycle2 = {}
        if segment:
            device_by_seg = [key for key in self.segment.keys() if self.segment[key] == segment]
        if device_type:
            if not segment:
                list_to_lookup = list(self.wholedict.keys())
            else:
                list_to_lookup = device_by_seg
            for d in list_to_lookup:
                if self.wholedict[d]['device_type'] in device_type:
                    cycle1[d] = self.wholedict[d]
        else:
            if not segment:
                cycle1 = self.wholedict
            else:
                for d in device_by_seg:
                    cycle1 [d] = self.wholedict[d]
        if levels:
            for d in cycle1.keys():
                if self.levels[d] in levels:
                    cycle2[d] = cycle1[d]
        else:
            cycle2 = cycle1
        return cycle2
    
    def setconfig(self, device, commands, log = False):
        dev = self.choose(device, withoutname = True)
        result = send_config_commands(dev, commands, log)
        return result
    
    
    def getinfo(self, device, func, *args, othercmd = False, txtFSMtmpl = False):
        '''
        The function receives the output of a command (func) from network equipment 'device' 
        command maybe "standard" (see dictionary 'commands') with arguments if they needed, or
        maybe ANY command then the 'othercmd variable must be set to True
        if txtFSMtmpl = template file name is specified
        function returns a list of lists obtained using the corresponding textfsm template
        if no - returns the direct output of the entered command
        '''
        if not othercmd:
            commands ={
                'neighbor_br': {'cisco_ios':f'show cdp neighbor detail','huawei':f'display lldp neighbor'},
                'arp': {'cisco_ios':f'show arp | in {args[0]}  +','huawei':f'display  arp | in {args[0]}  +','checkpoint_gaia': 'arp -an'},
                'neighbor_by_port': {'port': args[0]},
                'ethchannel_member': {'cisco_ios':f'show etherchannel {args[0]} port','huawei':f'display eth-trunk {args[0]}'},
                'mac_address_table': {'cisco_ios':f'show mac address-table | in {args[0]}','huawei':f'display mac-address | in {args[0]}'}
                }
        if func == 'neighbor_by_port':
            port = commands[func]['port']
            m = re.search(r'(Eth-Trunk|Po)(\S+)', port)
            if m:
                port = self.getinfo(device, 'ethchannel_member', m.group(2))[0][0][0]
            nblist = self.getinfo(device,'neighbor_br', 'pusto')
            subintf = re.compile(r'\.\d+')
            p = subintf.search(port)
            if p:
                intf = port[0:p.start(0)]
            else:
                intf = port
            for neighbor in nblist:
                lp =  subintf.search(neighbor[1])
                if lp:
                    intl = neighbor[1][0:lp.start(0)]
                else:
                    intl = neighbor[1]
                if intf == intl:
                    return neighbor[0]
            return False
        else:
            status = True
            dev = self.choose(device, withoutname = True)
            if not othercmd:
                command = commands[func][dev['device_type']]
            else:
                command = func
                #print(f'ОТЛАДКА: getinfo по идее должны оказаться здесь command = {command}')
            todo = send_show_command(dev, command)
            if not todo:
                return False
            if not txtFSMtmpl:
                if not othercmd:
                    if func == 'ethchannel_member':
                        if 'WorkingMode: LACP' in todo:
                            func = 'ethchannel_member_lacp'
                    outlist = templatizator(todo, func, dev['device_type'])
                else:
                    outlist = todo
            else:
                outlist = templatizator(todo, txtFSMtmpl, special = True)
            if func == 'mac_address_table':
                outlist[0][2] = port_name_normalize(outlist[0][2])
                commandmore = {
                    'cisco_ios':f'show mac address-table int {outlist[0][2]}',
                    'huawei':f'display mac-address {outlist[0][2]}'
                }
                command = commandmore[dev['device_type']]
                todo = send_show_command(dev, command)
                outwhole = templatizator(todo, 'mac_address_table', dev['device_type'])
                if len(outwhole) > 2:
                    if len(outwhole) == 3: #если компютер включен через IP телефон то светится 2 MAC в 2-х VLAN
                        for mac in myini.phone_mac:#у нас все телефоны имеют MAC начинающийся на 805e но ведь могут появиться и другие
                            if mac in outwhole[2][0]:
                                return [outlist[0][2], status]
                    else:
                        status = False
                return [outlist[0][2], status]
            '''
            if func == 'arp':
                new_out = []
                if len(outlist) > 1:
                    for line in outlist:
                        if line[0] == args[0]:
                            new_out.append(line)
                            break
                    if new_out:
                        outlist = new_out
            '''
            if not outlist:
                return False
            else:
                return outlist

    def _unnecessary_truncate(self, lines):
        i = 0
        for line in lines:
            if not line.startswith('Current configuration :'):
                i +=1
            else:
                break
        del lines[0:i]
        lines[0] = ''
        return lines
            
    def get_curr_config(self, device, list_ = True):
        '''
        the function returns the current configuration
        '''
        commands = {'cisco_ios': 'show running', 'huawei': 'display current'}
        device_type = self.choose(device, withoutname = True)['device_type']
        command = commands[device_type]
        _config = self.getinfo(device, command, othercmd = True)
        config = [line for line in _config.split('\n')]
        if device_type == 'cisco_ios':
            config = self._unnecessary_truncate(config)
        if list_:
            return config
        else:
            content = str()
            for line in config:
                content += '\n'.join(line)
            return content


class ActivkaBackup(Activka):
    '''
    Class is child of class Activka, used for config backup
    '''
    
    data = []
    def __init__(self, byname, byip):
        super().__init__(byname, byip)
        import socket
        self.main_backup_server = {}
        self.second_backup_server = {}
        self.main_backup_server['name'] = myini.main_backup_server['name']
        self.main_backup_server['protocol'] = 'local'
        self.main_backup_server['ftp_root'] = myini.main_backup_server['ftp_root']
        self.main_backup_server['ftp_user'] = myini.main_backup_server['user']
        self.main_backup_server['ftp_password'] = myini.main_backup_server['password']
        self.main_backup_server['local_root'] = myini.main_backup_server['local_root']
        self.second_backup_server['name'] = myini.second_backup_server['name']
        self.second_backup_server['protocol'] = 'ftp'
        self.second_backup_server['ftp_root'] = myini.second_backup_server['ftp_root']
        self.second_backup_server['ftp_user'] = myini.second_backup_server['user']
        self.second_backup_server['ftp_password'] = myini.second_backup_server['password']
        self.get_backup_list = self._get_backup_list_local
        self.get_backup_config = self._get_backup_config_local
        self.write_backup = self._write_backup_local
        
        
        if not socket.gethostname() == self.main_backup_server['name']:
            self.main_backup_server['protocol'] = 'ftp'
            self.get_backup_list = self._get_backup_list_ftp
            self.get_backup_config = self._get_backup_config_ftp
            self.write_backup = self._write_backup_ftp
    
    def _set_ftp_var(self, second):
        if second:
            ftp_params = {
                'host': self.second_backup_server['name'],           
                'user': self.second_backup_server['ftp_user'],       
                'passwd': self.second_backup_server['ftp_password'],
                'acct' : self.second_backup_server['ftp_user'],
                } 
            ftp_root  = self.second_backup_server['ftp_root']
        else:
            ftp_params = {
                'host': self.main_backup_server['name'],           
                'user': self.main_backup_server['ftp_user'],       
                'passwd': self.main_backup_server['ftp_password'],
                'acct' : self.main_backup_server['ftp_user'],
                } 
            ftp_root  = self.main_backup_server['ftp_root']
        return (ftp_root, ftp_params)
    

        
    
    def _get_backup_list_local(self, segment, device= False):
        '''
        The function returns a list of all backup files in the segment folder if device= False
        and only related to a specific device if the name device is specified
        '''
        from os import  path
        where = path.join(self.main_backup_server['local_root'], segment)
        files = [f for _, _, f in os.walk(where)][0]
        out = self._get_files_of_dir(files, device)
        return out
    

    def _get_backup_list_ftp(self, segment, device= False, second = False):
        '''
        The function returns a list of all backup files in the ftp_root/segment folder if device= False
        and only related to a specific device if the name device is specified
        '''
        from ftplib import FTP
        ftp_root, ftp_params = self._set_ftp_var(second)
        
        with FTP(**ftp_params) as con:
            con.cwd(ftp_root + segment)
            files = con.nlst()
        out = self._get_files_of_dir(files, device)
        return out
    
    def _get_files_of_dir(self, *args):
        '''
        args[0] = files
        args[1] = device
        '''
        file_list = []
        date_list = []
        for filename in args[0]:
            if not args[1]:
                file_list.append(filename)
            else:
                if f'{args[1].lower()}-' in filename.lower():
                    file_list.append(filename)
                    date_list.append(int(filename[-8:]))
        if args[1]:
            if not file_list:
                file_list = ['STOP LOSHADKA']
                date_list = [19000101]
            out = [file_list, date_list]
            return out
        else:
            return file_list
    
    
    def _get_backup_config_local(self, *args, list_ = True, date_ = -1):
        '''
        The function returns by default the last config backup for the device 'device' 
        in the form of list of string (if variable list_ = True) or as string if list_ = False
        args[0] = segmet
        args[1] = device
        '''
        from os import path
        f = self._get_backup_list_local(args[0], args[1])
        if not f:
            return False
        filename = path.join(self.main_backup_server['local_root'], args[0], f[0][date_])
        out = []
        with open(filename) as fr:
            for line in fr:
                line = line.rstrip()
                out.append(line)
        if list_:
            return out
        else:
            return '\n'.join(out)
    

    def _get_backup_config_ftp(self, segment, device= False, list_ = True, date_ = -1, second = False):
        '''
        Function return last config backup for device (by default) or if date_ != -1 then 
        the date_ in order from entire list of files (backup of configs) 
        in the form of a list of strings or as a single string if list_ = False
        args[0] = segment
        args[1] = device
        '''
        from ftplib import FTP

        f = self._get_backup_list_ftp(segment, device)
    
        if f[0][date_] == 'STOP LOSHADKA':
            return False
        cmd = 'RETR ' + f[0][date_]
        if cmd == 'RETR STOP LOSHADKA':
            return False
        data = []
        ftp_root, ftp_params = self._set_ftp_var(second)
        
        def handleDownload(more_data):
            data.append(more_data)
        with FTP(**ftp_params) as con:
            con.cwd(ftp_root + segment)
            con.retrbinary(cmd, callback = handleDownload)
        out = b''.join(data)
        out = out.decode(encoding = 'utf-8').split('\n')
        for i, line in enumerate(out):
            if '\x03' in line:
                out[i] = line.replace('\x03', '^C')
        out = [line.rsplit('\r')[0] for line in out] 
        if list_:
            return out
        else:
            content = str()
            for line in out:
                content += '\n'.join(line)
            return content


    def save_config_backup(self, *args, rewrite = False):
        '''
        args[0] = segmet
        args[1] = device
        '''
        import datetime
        td = datetime.date.today()
        today = f'{td.year}' + f'{td.month:02d}' + f'{td.day:02d}'
        curr_config = self.get_curr_config(args[1])
        last_backup = self.get_backup_config(*args)
        filename = args[1] + '-' + today
        curr_content = str()
        for line in curr_config:
            curr_content += '\n'.join(line)
        if not last_backup:
            self.write_backup(args[0], filename, curr_config)
            quit()
        last_content = str()
        for line in last_backup:
            last_content += '\n'.join(line)
        if curr_content == last_content:
            quit()
        else:
            if check_exeption(curr_config, last_backup):
                quit()
        filename_last = self.get_backup_list(*args)[0][-1]
        if filename == filename_last:
            if rewrite:
                self.write_backup(args[0], filename, curr_config)
        else:
            self.write_backup(args[0], filename, curr_config)
    
    

    def _write_backup_local(self, *args):
        from os import  path
        segment = args[0]
        filename = args[1]
        curr_config = args[2]
        content = '\n'.join(curr_config)
        where = path.abspath(path.join(self.main_backup_server['local_root'], segment, filename))
        with open(where, 'w') as fw:
            fw.write(content)
        self._write_backup_ftp(*args, second = True)
    

    def _write_backup_ftp(self, segment, filename, curr_config, second = False  ):
        '''
        args[0] = segment
        args[1] = filename
        args[2] = curr_config
        '''
        from ftplib import FTP
        from tempfile import gettempdir
        from os import path
        
        curr_config = '\n'.join(curr_config)
        cmd = f"STOR {filename}"
        tmpfile = path.abspath(path.join(gettempdir(), filename))
        ftp_root, ftp_params = self._set_ftp_var(second)
        with open(tmpfile, 'w') as fw:
            fw.write(curr_config)
        with FTP(**ftp_params) as con:
            con.cwd(ftp_root + segment)
            con.storlines(cmd, open(tmpfile, 'rb'))
        os.remove(tmpfile)


