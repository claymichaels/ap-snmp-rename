#!/usr/bin/python
__author__ = 'Clay'

from os.path import isfile
from sys import argv, path

path.insert(0, '/home/automation/scripts/clayScripts/resources/')
import claylib


# SNMP details
write_password = '<SNIPPED SNMP V2 PW>'
read_password = '<SNIPPED SNMP V2 PW>'
snmp_set_prefix = 'snmpset -v 2c -c'
snmp_get_prefix = 'snmpget -v 2c -c'
oids = {'sysName': '1.3.6.1.2.1.1.5.0', 'sysLocation': '1.3.6.1.2.1.1.6.0'}


# FM credentials
fmdb_ip = '<SNIPPED IP>0'
fmdb_user = '<SNIPPED USER>'
fmdb_password = '<SNIPPED PW>'


# Naming variables
fleet = 'Amfleet1'
brain_car_alias = 'Bistro'
sub_car_alias = 'Coach'


# db details
local_db_name = '/home/automation/scripts/clayScripts/websites/clay/resources/ap_rename.db'


def do_it(db, ip, sys_name, sys_location, con):
    try:
        # Set then check the sysName
        set_name_cmd = ' '.join([snmp_set_prefix, write_password, ip, oids['sysName'], 's', sys_name])
        sys_name_result = con.execute_command(set_name_cmd)

        # Set then check the sysLocation
        set_location_cmd = ' '.join([snmp_set_prefix, write_password, ip, oids['sysLocation'], 's', sys_location])
        sys_location_result = con.execute_command(set_location_cmd)

        if sys_name in sys_name_result and sys_location in sys_location_result:
            query = 'UPDATE Records SET Status="True" WHERE IP="%s";' % ip
            db.query(query)
            return True
        else:
            return False
    except KeyboardInterrupt:
        exit()


def build_db():
    local_db = claylib.Sqlite_db(local_db_name)
    if isfile(local_db_name):
        local_db.open()
    else:
        local_db.create('Records',['Car TEXT', 'IP TEXT', 'SysName TEXT', 'SysLocation TEXT', 'Status TEXT'])

    # get list of brains
    query = 'select obj_carriage.carriage_ref from dev_ccu inner join obj_carriage on dev_ccu.carriage_id=obj_carriage.carriage_id where obj_carriage.fleet_id="13";'
    response = claylib.query_fleetman_db(fmdb_ip, fmdb_user, fmdb_password, query)
    ccu_list = []
    for line in response:
        ccu_list.append(line[0])

    # Get list of APs
    query = 'select obj_carriage.carriage_ref, dev_access_point.ip_address from dev_access_point inner join obj_carriage on dev_access_point.carriage_id=obj_carriage.carriage_id where obj_carriage.fleet_id="13";'
    response = claylib.query_fleetman_db(fmdb_ip, fmdb_user, fmdb_password, query)
    for line in response:
        if (line[0] is not None) and (line[1] is not None):
            values_dict = {'Car': '', 'IP': '', 'SysName': '', 'SysLocation': '', 'Status': ''}
            values_dict['Car'] = line[0]
            values_dict['IP'] = line[1]
            ip_is_odd = int(values_dict['IP'][-1]) % 2
            if ip_is_odd:
                end = 'A-End'
            else:
                end = 'B-End'
            if values_dict['Car'] in ccu_list:
                brain = brain_car_alias
            else:
                brain = sub_car_alias
        values_dict['SysName'] = "%s" % '~'.join([fleet, 'AP', values_dict['IP']])
        values_dict['SysLocation'] = "%s" % '~'.join([values_dict['Car'], brain, end])
        cmd_str = 'INSERT INTO Records (Car,IP,SysName,SysLocation,Status) ' \
                  'VALUES ("%s","%s","%s","%s","%s")' % (values_dict['Car'], values_dict['IP'], values_dict['SysName'], values_dict['SysLocation'], 'False')
        #print cmd_str
        local_db.query(cmd_str)


# For loop!
def main():
    #build_db()
    local_db = claylib.Sqlite_db(local_db_name)
    local_db.open()
    ips_needing_update = local_db.query('SELECT IP FROM Records WHERE Status="False";')
    ip_list = []
    if argv[-1] == 'all':
        ccu_list = local_db.query('SELECT DISTINCT Car FROM Records WHERE SysLocation LIKE "%Bistro%";')
    else:
        ccu_list = [argv[-1]]
    for ccu in ccu_list:
        print('%s - Scanning for APs...' % ccu)
        try:
            ccu_con = claylib.Connection('root', 'helpdesk','amfleet1.%s' % ccu)
            consist2 = ccu_con.execute_command('cat /var/local/consist2.txt').split('\n')
            for line in consist2:
                if line[:9] in ['10.125.9.', '10.125.10', '10.125.11', '10.125.12', '10.125.13', '10.125.14']:
                    if line.split(' ')[0] in ips_needing_update:
                        ip_list.append(line.split(' ')[0])
            if len(ip_list) is 0:
                print('\tAll APs in consist are already updated!')
            #print(ip_list)
            for ip in ip_list:
                query = 'SELECT SysName FROM Records WHERE IP="%s";' % ip
                sysName = local_db.query(query)[0]
                query = 'SELECT SysLocation FROM Records WHERE IP="%s";' % ip
                sysLocation = local_db.query(query)[0]
                print('\t%s : Done?%s' % (ip, do_it(local_db, ip, sysName, sysLocation, ccu_con)))
            ip_list = []
            ccu_con.disconnect()
        except KeyboardInterrupt:
            exit()
        except:
            print('\tUnable to connect to %s' % ccu)
    query = 'SELECT COUNT(*) FROM Records;'
    total = local_db.query(query)[0]
    query = 'SELECT COUNT(*) FROM Records WHERE Status="True";'
    done = local_db.query(query)[0]
    print('Progress:%s/%s (%d%%)' % (done, total, ((float(done) / float(total))*100) ))

main()
