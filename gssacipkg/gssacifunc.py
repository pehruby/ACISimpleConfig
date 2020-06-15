import json
import requests
import urllib3
import sys
import re
import yaml
import os
from jinja2 import Template, UndefinedError


class ACIconfig:
    """Class which contains and manages ACI configuration dict

    """

    aciitemcfg = {}  # item configuretion structure
    configfiledir = ""  # absolute path to configfiles dir

    def __init__(self, acicfgfile, aciapidict, excel=False):
        """[summary]
        
        :param acicfgfile: config struct
        :type acicfgfile: [type]
        """

        self.aciapidict = aciapidict
        self.aciitemcfg["aci_items"] = {}
        if excel:
            # if Excel, this parameter already contains struct variable, not a filename
            aci_cfg = acicfgfile
        else:

            aci_cfg = []
            self.acicfgfile = acicfgfile
            curdir = os.getcwd()
            tmpfilename = os.path.join(curdir, self.acicfgfile)
            # absolute path to configfile
            self.acicfgfile = os.path.abspath(os.path.realpath(tmpfilename))
            # directory where are config files located
            self.configfiledir = os.path.dirname(self.acicfgfile)
            aci_cfg = self.read_configfile(self.acicfgfile)
        self.process_aci_config(aci_cfg, excel)

    def read_configfile(self, cfgfile):
        """ Read a configuration file into cfgfilevar
        
        :param cfgfile: [description]
        :type cfgfile: [type]
        :return:  structured config (lists,dicts)
        :rtype: [type]
        """
        # absolute path to filename
        cfgfile = os.path.join(self.configfiledir, cfgfile)
        cfgfile = os.path.normpath(cfgfile)
        if os.path.isfile(cfgfile):
            try:
                with open(cfgfile) as data_file:
                    cfgfilevar = data_file.read()
            except IOError:
                print("Unable to read the file", cfgfile)
                exit(1)
        else:
            print("Cannot find the file", cfgfile)
            exit(1)
        return cfgfilevar

    def yaml2struct(self, cfgfilevar):
        """Transform configuration yaml file stored in cfgfilevar into structured data
        
        :param cfgfilevar: [description]
        :type cfgfilevar: [type]
        :return: [description]
        :rtype: [type]
        """
        struct = yaml.safe_load(cfgfilevar)
        return struct

    def process_aci_config(self, acicfgfile, is_cfg_struct=False, isj2=False, vars={}):
        """Process configuration file stored in acicfgfile (plain text)
       
        :param acicfgfile: [description]
        :type acicfgfile: [type]
        :param isj2: is is jinja2 file?
        :type isj2: Boolean
        :param vars: [description], defaults to {}
        :type vars: dict, optional
        """
        urlparams = {}
        # if file is a j2 template
        if isj2:
            acicfgtemplate = Template(acicfgfile)
            # render final yaml configuration file from j2 template
            acicfgfile = acicfgtemplate.render(vars)
            # print(acicfgfile)
        if is_cfg_struct:       # acicfgfile is in fact not a yaml file but a python data structure
            acicfg = acicfgfile
        else:
            # convert yaml file into structured data
            acicfg = self.yaml2struct(acicfgfile)
        # process standard ACI config structure
        if "imdata" in acicfg:
            for subtree in acicfg["imdata"]:
                self.process_tree(subtree, urlparams)
        # 'default" names of parameters which are used in urlparams
        # (aciapidesc)
        # when full config tree is not specifies in aci_tree
        # i.e. fvTenant is not specified
        if "url_names" in acicfg:
            urlparams = acicfg["url_names"]
        # extract variables from configuration file
        # if vars var conigured in j2 template, they will be used in
        # child files
        if "vars" in acicfg:
            for varitem in acicfg["vars"].keys():
                vars[varitem] = acicfg["vars"][varitem]
        # transofm final yaml config into structured data
        # acicfg = self.yaml2struct(renderedcfg)
        if (
            "aci_trees" in acicfg and "aci_items" not in acicfg
        ):  # tree based configuration
            for subtree in acicfg["aci_trees"]:
                self.process_tree(subtree, urlparams)
        elif ("aci_items" in acicfg):
            #self.aciitemcfg["aci_items"] = acicfg["aci_items"]  # !!! THIS SHOULD BE DONE BETTER !!!
            self.process_items_cfg(acicfg["aci_items"])
        # config file contains reference to another config file
        if "aci_cfgfiles" in acicfg:
            for filename in acicfg["aci_cfgfiles"]:
                # absolute path to the file
                filename = os.path.join(self.configfiledir, filename)
                filename = os.path.normpath(filename)
                aci_cfg = self.read_configfile(filename)
                # is filename j2 template ?
                isj2 = filename.split(".")[-1] == "j2"
                self.process_aci_config(aci_cfg, False, isj2, vars)
 
    def process_items_cfg(self, itemscfg):
        """Process list of item based configuration. Add them to final item configuration
        structure self.aciitemcfg
        """

        for item in itemscfg:
            key = list(item.keys())[0]
            if key not in self.aciitemcfg["aci_items"]:
                self.aciitemcfg["aci_items"][key] = []

            self.aciitemcfg["aci_items"][key].append(item[key])
            
    def process_tree(self, subtree, urlparams):
        """Process a tree based configuration and create item based configuration ['aci_items']
        Recurent function

        :param subtree: subtree wich is being processd
        :type subtree: [type]
        :param urlparams: parameters used in POST URL
        :type urlparams: [type]
        """

        newitem = {}
        mykey = list(subtree)[0]  # currently processed item of the cfg tree
        stopproc = False  # dont't recurse down the tree, stop processing this branch

        if mykey not in self.aciapidict:
            print("cannot process key {}".format(mykey))
            return
        # stop processing this branch, save all children together with this item
        if "stopproc" in self.aciapidict[mykey]:
            if (
                self.aciapidict[mykey]["stopproc"] == "True"
                or self.aciapidict[mykey]["stopproc"] == "Yes"
            ):
                stopproc = True

        if mykey not in self.aciitemcfg["aci_items"]:
            self.aciitemcfg["aci_items"][mykey] = []
        for itemkey in subtree[mykey]:
            # save all children together with this item if stopproc == True
            # if stopproc == False continue with processing of children
            if itemkey == "children" and not stopproc:
                continue
            # copy is important, it removes link to original subtree (dict) location
            # this is problem when the dict is dumped into yaml
            newitem[itemkey] = subtree[mykey][itemkey].copy()
        for itemkey in urlparams:  # add names of parent items
            newitem[itemkey] = urlparams[itemkey].copy()
        self.aciitemcfg["aci_items"][mykey].append(newitem)
        if mykey not in urlparams:
            urlparams[mykey] = dict()
        if mykey in self.aciapidict and "key" in self.aciapidict[mykey]:
            # if key attribute is specified, use it insted of name attribute
            for keyattribute in self.aciapidict[mykey]["key"]:
                # keyattribute = self.aciapidict[mykey]['key']
                if keyattribute in subtree[mykey]["attributes"]:
                    urlparams[mykey][keyattribute] = subtree[mykey]["attributes"][
                        keyattribute
                    ]
        if "name" in subtree[mykey]["attributes"]:
            # if 'name' is attribute of current key (mykey), add it even it is not
            # specified in 'key' section of API description file
            # urlparams contain names of all superior items in current tree branch
            # i.e fvAEP will contain name of superior fvAP and fvTenant
            # template wich creates URL uses this urlparams dict
            urlparams[mykey]["name"] = subtree[mykey]["attributes"]["name"]
        if (
            "children" in subtree[mykey] and not stopproc 
        ):  # does current item contain child(ren)?
            try:
                for key in subtree[mykey]["children"]:  # yes, process it
                    # copy is important, otherwise the same variable is referenced
                    self.process_tree(key, urlparams.copy())
            except TypeError:   # no children are defined
                None

    def getconfig(self):
        return self.aciitemcfg

    def getitemconfig(self):  # ????
        itemcfg = {"aci_items": self.aciitemcfg["aci_items"]}
        return itemcfg


class ACIobj:
    """Class which manages an ACI instance
    Authentication, configuration depolyment

    """

    # J2 template for POST body
    body_template = Template(
        '{ \
        {{resourcetype}}: { \
            "attributes": { \
                {% for (key,value) in item.attributes.items() %}   \
                            "{{key}}": "{{value}}" {% if not loop.last %},{% endif %} \
                {% endfor %} \
            } \
        } \
    }'
    )

    def __init__(self, username, password, ip, ACIcfgobject, aciapilist):
        """[summary]

        :param username: ACI username
        :type username: [type]
        :param password: ACI password
        :type password: [type]
        :param ip: ACI IP or hostname
        :type ip: [type]
        :param ACIcfgobject: ACI configuration
        :type ACIcfgobject: [type]
        :param aciapilist: list of ACI API URLs for configuration items
        :type aciapilist: [type]
        """

        self.username = username
        self.password = password
        self.ip = ip
        self.acicfg = ACIcfgobject.getconfig()
        self.aciapilist = aciapilist  # list of API config URLs for specific ACI items
        self.aciapidict = {}  # dict of API config URLs for specific ACI items
        self.aciapiitems = []  # list of keys (ACI items) in aciapidict
        self.cookie = {}  # ACI auth cookie

        self.get_acicookie()  # is it OK? how long is cookie valid?
        self.processaciapicfg()
        self.notmodif = 0
        self.modif = 0
        self.deleted = 0
        self.created = 0

    def processaciapicfg(self):
        # transform list into dict, and to list of configuration item keys
        for item in self.aciapilist["aciapidesc"]:
            for key in item.keys():
                # dict of URLs for item configuration (i.e /api/mo/uni.json for
                # fvTenant config)
                self.aciapidict[key] = item[key]
                # list of configuration item keys (i.e. fvTenant, fvCtx, ...).
                # The order of keys is important
                self.aciapiitems.append(key)

    def get_acicookie(self):
        """Get auth token from ACI and create cookie entry

        :param username: [description]
        :type username: [type]
        :param password: [description]
        :type password: [type]
        :param ip: [description]
        :type ip: [type]
        :return: [description]
        :rtype: [type]
        """

        urllib3.disable_warnings()
        from urllib3.exceptions import InsecureRequestWarning

        urllib3.disable_warnings(InsecureRequestWarning)
        json_header = {"Content-type": "application/json"}

        # create credentials structure
        name_pwd = {
            "aaaUser": {"attributes": {"name": self.username, "pwd": self.password}}
        }
        json_credentials = json.dumps(name_pwd)
        # print (1)

        # log in to API
        login_url = "https://" + self.ip + "/api/aaaLogin.json"
        post_response = requests.post(
            login_url, headers=json_header, data=json_credentials, verify=False
        )

        if post_response.status_code != 200:
            print("Authrentication failed with code:", post_response.status_code)
            exit(1)

        # get token from login response structure
        auth = json.loads(post_response.text)
        login_attributes = auth["imdata"][0]["aaaLogin"]["attributes"]
        auth_token = login_attributes["token"]
        # create cookie array from token
        self.cookie = {}
        self.cookie["APIC-Cookie"] = auth_token

    def aci_api_post(self, path, body):

        urllib3.disable_warnings()
        from urllib3.exceptions import InsecureRequestWarning

        urllib3.disable_warnings(InsecureRequestWarning)
        json_header = {"Content-type": "application/json"}

        url = "https://" + self.ip + path + "?rsp-subtree=modified"
        post_response = requests.post(
            url, headers=json_header, data=body, cookies=self.cookie, verify=False
        )

        return post_response

    def process_aci_post_resp(self, api_item, response):
        """Process the response from the API POST call

        :param api_item: [description]
        :type api_item: [type]
        :param response: [description]
        :type response: [type]
        """

        status = "not modified"  # if imdate list is empty, the item was not modified
        errmsg = ""
        resp_body = json.loads(response.text)
        if response.status_code == 200:
            if resp_body["imdata"]:
                if "status" in resp_body["imdata"][0][api_item]["attributes"]:
                    status = resp_body["imdata"][0][api_item]["attributes"][
                        "status"
                    ]  # does imdata contain a status?
            print(
                "- {}/{}, ACI config {}".format(
                    response.status_code, response.reason, status
                )
            )
            # update config modification statistics
            if "not modified" in status:
                self.notmodif += 1
            elif "modified" in status:
                self.modif += 1
            elif "deleted" in status:
                self.deleted += 1
            elif "created" in status:
                self.created += 1
        else:
            if resp_body["imdata"]:
                if "error" in resp_body["imdata"][0]:
                    errmsg = resp_body["imdata"][0]["error"]["attributes"][
                        "text"
                    ]  # does imdata contain a error text?
            print(
                "- {}/{}, Error msg: {}".format(
                    response.status_code, response.reason, errmsg
                )
            )
            sys.exit(1)

    def print_stat(self):

        print("{} items created".format(self.created))
        print("{} items modified".format(self.modif))
        print("{} items not modified".format(self.notmodif))
        print("{} items deleted".format(self.deleted))

    def aci_create_url(self, cfg, urltmpl):
        """Create URL from the template

        :param cfg: [description]
        :type cfg: [type]
        :param urltmpl: [description]
        :type urltmpl: [type]
        """

        # url = urltmpl.render(cfg)
        j2varlist = []

        if not isinstance(urltmpl, list):  # urltmpl is not a list
            urlTemplate = Template(urltmpl)
        else:  # urltempl is a list
            for item in urltmpl:  # find the proprer url template for the current cfg
                j2varlist = re.findall(r"{{([a-zA-Z0-9]+)\.", item)
                j2itemfound = True
                for j2varitem in j2varlist:  # are all j2 variables in cfg as keys ?
                    if j2varitem not in cfg:
                        j2itemfound = False  # ... no, wrong URL template
                        break
                if j2itemfound:  # ... yes, the proper URL template was found
                    urlTemplate = Template(item)
                    break
        try:
            url = urlTemplate.render(cfg)
        except (UnboundLocalError, UndefinedError):
            print("Proper URL template was not found", cfg)
            exit(1)
        return url

    def get_list_of_j2_vars(self, item):
        None

    def aci_create_body(self, cfgtype, cfg, bodytmpl):
        """Create POST body from the template

        :param cfgtype: [description]
        :type cfgtype: [type]
        :param cfg: [description]
        :type cfg: [type]
        :param bodytmpl: [description]
        :type bodytmpl: [type]
        """

        body = bodytmpl.render(resourcetype=cfgtype, item=cfg)
        return body

    def aci_create_body2(self, cfgtype, cfg):
        """Create POST body
        
        :param cfgtype: [description]
        :type cfgtype: [type]
        :param cfg: [description]
        :type cfg: [type]
        :return: [description]
        :rtype: [type]
        """

        bodydict = {cfgtype: {}}

        bodydict[cfgtype]["attributes"] = cfg["attributes"].copy()
        if "children" in cfg:
            bodydict[cfgtype]["children"] = cfg["children"].copy()
        bodyjson = json.dumps(bodydict)
        return bodyjson

    def process_items(self, delete=False):
        """Proces element (item) based configuration
        elements/items are fvTenant, fvCtx, fvBD, ...
        These elemants are defined separately in the configuration file

        """
        """ probably not needed ....
        if delete:
            # proces items in reverse order if you want to delete them
            _apiitems = self.aciapiitems[::-1].copy()
        else:
        """
        _apiitems = self.aciapiitems

        # go throug all configuration item keys (i.e. fvTenant, fvCtx, ...)
        for api_item in _apiitems:
            if api_item in self.acicfg["aci_items"]:
                # go through of all items of specific type (i.e. fvTenant)
                for resource in self.acicfg["aci_items"][api_item]:
                    # print(resource)
                    if "desc" in self.aciapidict[api_item]:
                        print(
                            "Processing {} ({}) with {}".format(
                                api_item,
                                self.aciapidict[api_item]["desc"],
                                resource["attributes"],
                            )
                        )
                    else:
                        print(
                            "Processing {} with {}".format(
                                api_item, resource["attributes"]
                            )
                        )
                    url = self.aci_create_url(
                        resource, self.aciapidict[api_item]["urltempl"]
                    )  # create URL from the template
                    if delete:
                        resource["attributes"]["status"] = "deleted"
                    body = self.aci_create_body2(
                        api_item, resource
                    )  # create http POST body from the template
                    resp = self.aci_api_post(url, body)  # call ACI REST API
                    self.process_aci_post_resp(
                        api_item, resp
                    )  # process the response (write info, exit in case of error)

    def deploycfg(self):

        if "aci_items" in self.acicfg:  # element(item) based configuration
            self.process_items()
        self.print_stat()

    def deletecfg(self):

        if "aci_items" in self.acicfg:  # element(item) based configuration
            self.process_items(delete=True)
        self.print_stat()
