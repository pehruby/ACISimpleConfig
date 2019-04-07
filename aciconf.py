#! /usr/bin/env python

import yaml
import os
import argparse
import getpass

from gssacipkg import ACIobj, ACIconfig


def read_config_file(config_file):
    """Read an YAML config file
    :param config_file: [description]
    :type config_file: [type]
    """

    if os.path.isfile(config_file):
        try:
            with open(config_file) as data_file:
                config_json = yaml.safe_load(data_file.read())
        except IOError:
            print("Unable to read the file", config_file)
            exit(1)
    else:
        print("Cannot find the file", config_file)
        exit(1)

    return config_json


def main():

    username = ""
    pswd = ""
    aci_ip = ""
    config_file = ""
    aci_api_cfg_file = ""
    debug = False

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", help="debug", action="store_true", required=False
    )
    parser.add_argument("-i", "--ip", help="ACI IP address or hostname", required=True)
    parser.add_argument("-u", "--username", help="ACI username", required=True)
    parser.add_argument("-p", "--password", help="ACI password", required=False)
    parser.add_argument("-c", "--config", help="configuration file", required=True)
    parser.add_argument(
        "-a", "--aciapidesc", help="ACI API descriprion configuration", required=True
    )
    args = parser.parse_args()
    aci_ip = args.ip
    debug = args.debug  # noqa
    username = args.username
    pswd = args.password
    config_file = args.config
    aci_api_cfg_file = args.aciapidesc

    if pswd == "":
        pswd = getpass.getpass("Password:")

    acicfgcode = read_config_file(config_file)  # ACI IaC conf from a yaml file
    aciapilist = read_config_file(
        aci_api_cfg_file
    )  # list of API config URLs for specific ACI items

    MyACIconfig = ACIconfig(acicfgcode)
    MyACI = ACIobj(username, pswd, aci_ip, MyACIconfig, aciapilist)
    MyACI.deploycfg()
    print("End")


if __name__ == "__main__":

    main()
