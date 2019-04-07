#! /usr/bin/env python

from ruamel.yaml import YAML    # preserves dict order during the dump
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


def main():

    config_file = ""
    debug = False

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", help="debug", action="store_true", required=False
    )
    parser.add_argument("source", help="source config file")
    parser.add_argument("target", help="target file name")
    args = parser.parse_args()

    debug = args.debug  # noqa
    config_file = args.source
    target_file = args.target

    acicfgcode = read_config_file(config_file)  # ACI IaC conf from a yaml file

    MyACIconfig = ACIconfig(acicfgcode)

    target_config = MyACIconfig.getitemconfig()
    write_config_file(target_file, target_config)

    print("End")


if __name__ == "__main__":

    main()
