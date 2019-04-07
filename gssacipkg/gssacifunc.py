import json
import requests
import urllib3
import sys
from jinja2 import Template


class ACIconfig:
    """Class which contains and manages ACI configuration dict

    """

    def __init__(self, acicfg):
        self.acicfg = acicfg

        self.process_aci_config()

    def process_aci_config(self):
        urlparams = {}
        if (
            "aci_trees" in self.acicfg and "aci_items" not in self.acicfg
        ):  # tree based configuration
            self.acicfg["aci_items"] = {}
            for subtree in self.acicfg["aci_trees"]:
                self.process_tree(subtree, urlparams)

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

        if mykey not in self.acicfg["aci_items"]:
            self.acicfg["aci_items"][mykey] = []
        for itemkey in subtree[mykey]:
            if itemkey == "children":
                continue
            # copy is important, it removes link to original subtree (dict) location
            # this is problem when the dict is dumped into yaml
            newitem[itemkey] = subtree[mykey][itemkey].copy()
        for itemkey in urlparams:  # add names of parent items
            newitem[itemkey] = urlparams[itemkey]
        self.acicfg["aci_items"][mykey].append(newitem)
        if "name" in subtree[mykey]["attributes"]:
            # i hope that all name attributes of parent items are contained as
            # paremeters in URL of the child
            # add name of current item to parameters dict. It will be used during child
            # processing
            # urlparams contain names of all superior items in current tree branch
            # i.e fvAEP will contain name of superior fvAP and fvTenant
            # template wich creates URL uses this urlparams dict
            urlparams[mykey] = subtree[mykey]["attributes"]["name"]
        if "children" in subtree[mykey]:  # does current item contain child(ren)?
            for key in subtree[mykey]["children"]:  # yes, process it
                # copy is important, otherwise the same variable is referenced
                self.process_tree(key, urlparams.copy())

    def getconfig(self):
        return self.acicfg

    def getitemconfig(self):
        itemcfg = {'aci_items': self.acicfg['aci_items']}
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

    def aci_create_url(self, cfg, urltmpl):
        """Create URL from the template

        :param cfg: [description]
        :type cfg: [type]
        :param urltmpl: [description]
        :type urltmpl: [type]
        """

        url = urltmpl.render(urlparams=cfg)
        return url

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

    def process_items(self):
        """Proces element (item) based configuration
        elements/items are fvTenant, fvCtx, fvBD, ...
        These elemants are defined separately in the configuration file

        """
        # go throug all configuration item keys (i.e. fvTenant, fvCtx, ...)
        for api_item in self.aciapiitems:
            if api_item in self.acicfg["aci_items"]:
                # go through of all items of specific type (i.e. fvTenant)
                for resource in self.acicfg["aci_items"][api_item]:
                    url = self.aci_create_url(
                        resource, Template(self.aciapidict[api_item]["urltempl"])
                    )  # create URL from the template
                    body = self.aci_create_body(
                        api_item, resource, self.body_template
                    )  # create http POST body from the template
                    print(
                        "Processing {} with {}".format(api_item, resource["attributes"])
                    )
                    resp = self.aci_api_post(url, body)  # call ACI REST API
                    self.process_aci_post_resp(
                        api_item, resp
                    )  # process the response (write info, exit in case of error)

    def deploycfg(self):

        if "aci_items" in self.acicfg:  # element(item) based configuration
            self.process_items()
