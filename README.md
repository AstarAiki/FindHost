# FindHost
English:
fh.py - (find host) The script searches your local network for a host specified by IP or MAC address, or host name without specifying a domain.
Detailed help is available at fh -h

net_func.py A library of functions used to manipulate active network equipment. It is built using the netmiko module. I am using Cisco and Huawei equipment, but this library can also be used with equipment from other companies. 

the Templates directory contains textFSM templates for processing the command output

fh.ini - settings file for the fh script in YAML format. This format is simple and intuitive even for manual input and easy to read by python

Example:
	localpath: C:/ForWork/ - location of all files
	phone_mac: - the list of initial octets of IP phones, needed to identify on a switch port more than one MAC: phone or switch
	- 805e
	templpath: C:/ForWork/TEMPLATES/ - location of textFSM templates
	language: 'ru' - language of the program messages, made 'ru' Russian and 'en' English

messages_en.yaml, messages_ru.yaml - language files for program messages

activka_byname.yaml - dictionary of all switches and routers as
{device_name:{dictionary of connection variables required by the netmiko module}}

in the dictionary to connect, I use only the type of device and its IP, the username and password are the same, included in the initialization of the Activka class

to use net_func.py with other brands, you need to put in activka_byname.yaml's device_type like in netmiko 

for fh.py in this case, in the function Activka.getinfo() you need to add to the commands dictionary "standard" commands for this equipment and create templates textFSM

activka_byip.yaml - Dictionary of all IP addresses and names of devices. It is not used in the Activka class yet, but I have some ideas and it may be useful. It was obtained by me using already written Activka class with passing through all devices and parsing command (show ip int brief/display ip int)


Russian:
fh.py - (find host) Скрипт ищет в вашей локальной сети хост, указанный по IP или по MAC адресу, или имени хоста без указания домена.
Подробная справка доступна по fh -h

net_func.py библиотека функций, используемая для манипулирования активным сетевым оборудованием. Построена с использованием модуля netmiko. Я использую оборудование фирм Cisco и Huawei, но эту библиотеку возможно использовать и с оборудованием других фирм, надо только в вызове getinfo класса Activka расширить словарь commands. 

в каталоге Templates помещаются шаблоны textFSM для обработки вывода команд

fh.ini - файл настроек для скрипта fh в формате YAML. Этот формат прост и интуитивно понятен даже для ручного ввода и легко читается питоном

Пример:
	localpath: C:/ForWork/ 		- расположение всех файлов
	phone_mac: 		- список начальных октетов IP телефонов, необходим чтобы определить на порту коммутатора больше одного MAC это телефон или  коммутатор
	- 805e
	templpath: C:/ForWork/TEMPLATES/	- расположение шаблонов textFSM
	language: 'ru'		- язык сообщений программы, сделаны 'ru' русский и 'en' английский

messages_en.yaml, messages_ru.yaml - языковые файлы для сообщений программы

activka_byname.yaml - словарь всех коммутаторов и маршрутизаторов в виде
{имя_устройства:{словарь переменных для подключения требуемый модулем netmiko}}

в словаре для подключения использую только тип устройства и его IP, имя и пароль для подключения одинаковые, включены в инициализацию класса Activka

для использования net_func.py с оборудованием других фирм, надо в device_type файла activka_byname.yaml прописывать тип как указан в netmiko

для fh.py в этом случае в функции Activka.getinfo() необходимо в словарь commands добавить "стандартные" комманды соответсвующие этому оборудованию и создать шаблоны textFSM

activka_byip.yaml - словарь соответсвия всех IP адресов всех устройств и имени этих устройств. В классе Activka пока не используется, но есть мысли и может пригодиться. Был получен мною с помощью написанного уже класса Activka с проходом по всем устройствам и разбора команды (show ip int brief/display ip int)


