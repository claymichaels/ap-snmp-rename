# ap-snmp-rename
A tool to rename (via SNMP) several thousand Access Points according to a schema.

Uses Claylib (I regret the name) functions to connect to a database containing all devices for a customer, 
calculates the new SysName and SysLocation, 
then sets those variables remotely on each online AP via SNMPv2. 
All successful updates are recorded in seperate local SQLite3 database.
