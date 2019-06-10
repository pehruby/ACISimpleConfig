from ruamel.yaml import YAML  # preserves dict order during the dump
import os
import argparse

from gssacipkg import ACIconfig


def read_config_file(config_file):
    """Read an YAML config file
    :param config_file: [description]
    :type config_file: [type]
    """

    yaml = YAML()
    if os.path.isfile(config_file):
        try:
            with open(config_file) as data_file:
                config_json = yaml.load(data_file.read())
        except IOError:
            print("Unable to read the file", config_file)
            exit(1)
    else:
        print("Cannot find the file", config_file)
        exit(1)

    return config_json


def write_config_file(config_file, data):

    yaml = YAML()
    try:
        with open(config_file, "w+") as data_file:
            yaml.dump(data, data_file)
    except IOError:
        print("Unable to save the file", config_file)
        exit(1)


def list2dict(listvar):
    """Transform list to dict
    
    :param listvar: [description]
    :type listvar: [type]
    :return: [description]
    :rtype: [type]
    """
    resultdict = {}
    for item in listvar:
        key = list(item.keys())[0]
        resultdict[key] = item[key]
    return resultdict


def main():

    config_file = ""
    debug = False

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", help="debug", action="store_true", required=False
    )
    parser.add_argument("-s", "--source", help="source config file", required=True)
    parser.add_argument("-t", "--target", help="target file name", required=True)
    parser.add_argument(
        "-a", "--aciapidesc", help="ACI API descriprion configuration", required=True
    )
    args = parser.parse_args()

    debug = args.debug  # noqa
    config_file = args.source
    target_file = args.target
    aci_api_cfg_file = args.aciapidesc

    # acicfgcode = read_config_file(config_file)  # ACI IaC conf from a yaml file
    # acicfgcode = read_config_file(config_file)  # ACI IaC conf from a yaml file
    aciapilist = read_config_file(
        aci_api_cfg_file
    )  # list of API config URLs for specific ACI items
    aciapidict = list2dict(aciapilist["aciapidesc"])
    MyACIconfig = ACIconfig(config_file, aciapidict)

    target_config = MyACIconfig.getitemconfig()
    write_config_file(target_file, target_config)

    print("End")


if __name__ == "__main__":

    main()
