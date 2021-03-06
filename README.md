# ACI Simple Config

Cisco ACI configuration using REST API and templates

[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/pehruby/ACISimpleConfig)

## Description

A sample script which shows how Cisco ACI can be configured using REST API. Only certain ACI configuration items are supported (tenant, BD, vrf, AP, AEP, ...). 

The script deploys configuration specified in a YAML file to Cisco ACI. The YAML file follows the structure of ACI Management Information Model (see https://sandboxapicdc.cisco.com/visore.html)

The structure of the configuration file can be "tree" based. In this case the stucture of the configuration file exactly follows the tree structure of ACI MIM (incl. item names). See file ACItreecfg.yml

The second option is an "item" based configuration file where each configuration item is specified separately in the file. See file roles/tn_pehruby_test/vars/main.yml

The aciapidesc.yml contains API URL templates used to deploy the configuration. Only some API URLs are supported !!!

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

### Tenant configuration example

Deploy configuration specified in the ACItreecfg.yml file into Cisco ACI Sandbox using aciconf.py script

```text
 py -3 ./aciconf.py -u admin -p ciscopsdt -i sandboxapicdc.cisco.com -c ./ACItreecfg.yml -a ./aciapidesc.yml
```

The script accepts both "tree" and "item" based configuration yaml files

#### Excel as a source of template variables

```text
 py -3 ./aciconf.py -u admin -i sandboxapicdc.cisco.com -c ./excelfiles/bdotest.j2 -a ./aciapidesc.yml -x "./excelfiles/ACI_Parameters.xlsx;BDO;2"
```

Parameter -x contains excelFileName|excelSheetName|lineNrWhereTableBegins
Each line of the table is used as a source of variables which are used in the j2 file specified using -c parameter

Using the following table, one BD is created (if doesn't already exist) and one deleted (if isn't already deleted)

BDOname    | Status     | Tenant | Description | VRF 
-----------|------------|--------|-------------|-----
PHTEST1_BDO |  |XLSTEST_TEN | Test BDO 1 | TEST1_VRF
PHTEST2_BDO | deleted |XLSTEST_TEN | Test BDO 2 | TEST2_VRF

Appropriate Jinja2 template

```j2
url_names:
  fvTenant: 
    name: "{{Tenant}}"

aci_trees:
  - fvBD:   # BD
      attributes:
        name: "{{BDOname}}"
        status: "{{Status}}"
        multiDstPktAct: "bd-flood"
        unkMacUcastAct: proxy
      children:
        - fvRsCtx:  # vrf to BD binding
            attributes:
              status: "{{Status}}"
              tnFvCtxName: "{{VRF}}"
```

### Contracts

```text
py -3 ./aciconf.py -u admin -p ciscopsdt -i sandboxapicdc.cisco.com -c .\examples\contracts\testcontracts.yml -a ./aciapidesc.yml
```

### L4-L7 Service (GoTo, Redir)

```text
py -3 ./aciconf.py -u admin -p ciscopsdt -i sandboxapicdc.cisco.com -c .\examples\L4L7\GoToRedir.yml -a ./aciapidesc.yml
```
