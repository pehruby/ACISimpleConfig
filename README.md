# ACI Simple Config

Created for NetDevOps Live! Code Exchange Challenge

## Description

A sample script which shows how Cisco ACI can be configured using REST API. Only certain ACI configuration items are supported (tenant, BD, vrf, AP, AEP, ...). The script is not intended to be used in a production environment !

The script deploys configuration specified in a YAML file to Cisco ACI. The YAML file follows the structure of ACI Management Information Model (see https://sandboxapicdc.cisco.com/visore.html)

The structure of the configuration file can be "tree" based. In this case the stucture of the configuration file exactly follows the tree structure of ACI MIM (incl. item names). See file ACItreecfg.yml

The second option is an "item" based configuration file where each configuration item is specified separately in the file. See file roles/tn_pehruby_test/vars/main.yml

The "tree" based configuration is prefered. This configuration is supported by the python script aciconf.py only. Ansible playbook provided in this example doesn't support the "tree" based configuration.

The aciapidesc.yml contains API URL templates used to deploy the configuration. Only a few URLs are supported !!!

Script tree2flatconv.py transforms a "tree" based config into a "item" based.

## Clone the repository

```text
git clone https://github.com/pehruby/ACISimpleConfig.git
cd ACISimpleConfig

chmod 755 aciconf.py
chmod 755 tree2flatconv.py
```

## Python environment

Create virtual environment and activate it (optional)

```text
python3 -m venv venv
. venv/bin/activate
```

Install required modules

```text
pip install -r requirements.txt
```

## Usage examples

### Python script 

Deploy configuration specified in the ACItreecfg.yml file into Cisco ACI Sandbox using aciconf.py script

```text
 ./aciconf.py -u admin -p ciscopsdt -i sandboxapicdc.cisco.com -c ./ACItreecfg.yml -a ./aciapidesc.yml
```

The script accepts both "tree" and "item" based configuration yaml files

### Ansible

Deploy configuration specified in the roles/tn_pehruby_test/vars/main.yml into Cisco ACI Sandbox using an Ansible playbook
Ansible must be intalled on your workstation.

```text
ansible-playbook aci-deploy.yml
```

The playbook accepts "item" based configuration files only.






