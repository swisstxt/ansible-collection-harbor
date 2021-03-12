#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2021, Joshua Hügli <@joschi36>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: harbor_registry
author:
  - Joshua Hügli (@joschi36)
version_added: ""
short_description: Manage Harbor registries
description:
  - Create, update and delete Harbor registries over API.
options:
  #TODO
extends_documentation_fragment:
  - joschi36.harbor.api
'''

import copy
import json
import requests
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.swisstxt.harbor.plugins.module_utils.base import \
    HarborBaseModule


class HarborRegistryModule(HarborBaseModule):
    @property
    def argspec(self):
        argument_spec = copy.deepcopy(self.COMMON_ARG_SPEC)
        argument_spec.update(
            name=dict(type='str', required=True),
            type=dict(
                type='str',
                required=True,
                choices=['ali-acr', 'aws-ecr', 'azure-acr', 'docker-hub',
                'docker-registry', 'gitlab', 'google-gcr', 'harbor',
                'helm-hub', 'huawei-SWR', 'jfrog-artifactory', 'quay',
                'tencent-tcr', ]
            ),
            endpoint_url=dict(type='str', required=True),
            access_key=dict(type='str', required=False),
            access_secret=dict(type='str', required=False, no_log=True),
            insecure=dict(type='bool', required=False, default=False),

            state=dict(default='present', choices=['present'])
        )
        return argument_spec

    def __init__(self):
        self.module = AnsibleModule(
            argument_spec=self.argspec,
            supports_check_mode=True
        )

        super().__init__()

        self.result = dict(
            changed=False
        )

        existing_registry_request = requests.get(
            f"{self.api_url}/registries?q=name%3D{self.module.params['name']}",
            auth=self.auth
        )

        try:
            existing_registry = existing_registry_request.json()[0]
        except TypeError:
            existing_registry = False

        desired_registry = {
            'name': self.module.params['name'],
            'credential': {
                'type': '',
                'access_key': '',
                'access_secret': ''
            }
        }
        if self.module.params['insecure'] is not None:
            desired_registry['insecure'] = self.module.params['insecure']
        if self.module.params['type'] is not None:
            desired_registry['type'] = self.module.params['type']
        if self.module.params['endpoint_url'] is not None:
            desired_registry['url'] = self.module.params['endpoint_url']
        if self.module.params['access_key'] is not None:
            desired_registry['credential']['access_key'] = self.module.params['access_key']
            desired_registry['credential']['type'] = 'basic'
        if self.module.params['access_secret'] is not None:
            desired_registry['credential']['access_secret'] = self.module.params['access_secret']
            desired_registry['credential']['type'] = 'basic'

        if existing_registry:
            # Check & "calculate" desired configuration
            self.result['registry'] = copy.deepcopy(existing_registry)
            after_calculated = copy.deepcopy(existing_registry)
            after_calculated.update(desired_registry)

            # Ignore secret as it isn't returned with API
            del(existing_registry['credential']['access_secret'])
            del(after_calculated['credential']['access_secret'])

            if existing_registry == after_calculated:
                self.module.exit_json(**self.result)

            if self.module.check_mode:
                self.result['changed'] = True
                self.result['diff'] = {
                    "before": json.dumps(existing_registry, indent=4),
                    "after": json.dumps(after_calculated, indent=4),
                }

            else:
                set_request = requests.put(
                    f'{self.api_url}/registries/{existing_registry["id"]}',
                    auth=self.auth,
                    json=desired_registry,
                )

                if not set_request.status_code == 200:
                    self.module.fail_json(msg=self.requestParse(set_request))

                after_request =requests.get(
                    f'{self.api_url}/registries/{existing_registry["id"]}',
                    auth=self.auth
                )
                after = after_request.json()
                self.result['registry'] = copy.deepcopy(after)
                if existing_registry != after:
                    self.result['changed'] = True
                    self.result['diff'] = {
                        "before": json.dumps(existing_registry, indent=4),
                        "after": json.dumps(after, indent=4),
                    }

        else:
            if not self.module.check_mode:
                create_project_request = requests.post(
                    self.api_url+'/registries',
                    auth=self.auth,
                    json=desired_registry
                )
                if not create_project_request.status_code == 201:
                    self.module.fail_json(msg=self.requestParse(create_project_request))

                after_request =requests.get(
                    f"{self.api_url}/registries?q=name%3D{self.module.params['name']}",
                    auth=self.auth
                )
                self.result['registry'] = copy.deepcopy(after_request.json())

            self.result['changed'] = True

        self.module.exit_json(**self.result)

def main():
    HarborRegistryModule()

if __name__ == '__main__':
    main()
