#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2021, Joshua Hügli <@joschi36>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
self.module: harbor_project
author:
  - Joshua Hügli (@joschi36)
version_added: ""
short_description: Manage Harbor project
description:
  - Create, update and delete Harbor Configuration over API.
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

class HarborProjectModule(HarborBaseModule):
    @property
    def argspec(self):
        argument_spec = copy.deepcopy(self.COMMON_ARG_SPEC)
        argument_spec.update(
            name=dict(type='str', required=True),

            public=dict(type='bool', required=False),
            auto_scan=dict(type='bool', required=False),
            content_trust=dict(type='bool', required=False),

            quota_gb=dict(type='int', required=False),

            cache_registry=dict(type='str', required=False),

            state=dict(default='present', choices=['present'])
        )
        return argument_spec

    def __init__(self):
        self.module = AnsibleModule(
            argument_spec=self.argspec,
            supports_check_mode=True,
        )

        super().__init__()

        self.result = dict(
            changed=False
        )

        existing_project = self.getProjectByName(self.module.params['name'])

        project_desired_metadata = {}
        if self.module.params['auto_scan'] is not None:
            project_desired_metadata['auto_scan'] = str(self.module.params['auto_scan']).lower()
        if self.module.params['content_trust'] is not None:
            project_desired_metadata['enable_content_trust'] = str(self.module.params['content_trust']).lower()
        if self.module.params['public'] is not None:
            project_desired_metadata['public'] = str(self.module.params['public']).lower()

        if existing_project:
            # Handle Quota
            if self.module.params['quota_gb'] is not None:
                quota_request = requests.get(
                    f"{self.api_url}/quotas?reference_id={existing_project['project_id']}",
                    auth=self.auth
                )
                quota = quota_request.json()[0]
                actual_quota_size = quota['hard']['storage']
                desired_quota_size = self.quotaBits(self.module.params['quota_gb'])
                if actual_quota_size != desired_quota_size:
                    quota_put_request = requests.put(
                        f"{self.api_url}/quotas/{quota['id']}",
                        auth=self.auth,
                        json={
                            'hard': {
                                'storage': desired_quota_size
                            }
                        }
                    )
                    if quota_put_request.status_code == 200:
                        self.result['changed'] = True
                    elif quota_put_request.status_code == 400:
                        self.module.fail_json(msg="Illegal format of quota update request..", **self.result)
                    elif quota_put_request.status_code == 401:
                        self.module.fail_json(msg="User need to log in first.", **self.result)
                    elif quota_put_request.status_code == 403:
                        self.module.fail_json(msg="User does not have permission of admin role.", **self.result)
                    elif quota_put_request.status_code == 500:
                        self.module.fail_json(msg="Unexpected internal errors.", **self.result)
                    else:
                        self.module.fail_json(msg=f"""
                            Unknown HTTP status code: {quota_put_request.status_code}
                            Body: {quota_put_request.text}
                        """)


            # Check & "calculate" desired configuration
            self.result['project'] = copy.deepcopy(existing_project)
            after_calculated = copy.deepcopy(existing_project)
            after_calculated['metadata'].update(project_desired_metadata)

            if existing_project == after_calculated:
                self.module.exit_json(**self.result)

            if self.module.check_mode:
                self.result['changed'] = True
                self.result['diff'] = {
                    "before": json.dumps(existing_project, indent=4),
                    "after": json.dumps(after_calculated, indent=4),
                }

            else:
                set_request = requests.put(
                    f'{self.api_url}/projects/{existing_project["project_id"]}',
                    auth=self.auth,
                    json={
                        "metadata": project_desired_metadata
                    },
                )

                if not set_request.status_code == 200:
                    self.module.fail_json(msg=self.requestParse(set_request), **self.result)

                after_request =requests.get(
                    f'{self.api_url}/projects/{existing_project["project_id"]}',
                    auth=self.auth
                )
                after = after_request.json()
                self.result['project'] = copy.deepcopy(after)
                if existing_project != after:
                    self.result['changed'] = True
                    self.result['diff'] = {
                        "before": json.dumps(existing_project, indent=4),
                        "after": json.dumps(after, indent=4),
                    }

        else:
            if not self.module.check_mode:
                data = {
                    "project_name": self.module.params["name"],
                    "metadata": project_desired_metadata,
                }
                if self.module.params['quota_gb'] is not None:
                    data["storage_limit"] = self.quotaBits(self.module.params['quota_gb'])

                if self.module.params['cache_registry'] is not None:
                    registry_request = requests.get(
                        f"{self.api_url}/registries?q=name%3D{self.module.params['cache_registry']}",
                        auth=self.auth
                    )

                    try:
                        data['registry_id'] = registry_request.json()[0]['id']
                    except (TypeError, ValueError):
                        self.module.fail_json(msg="Registry not found", **self.result)

                create_project_request = requests.post(
                    self.api_url+'/projects',
                    auth=self.auth,
                    json=data
                )

                if not create_project_request.status_code == 201:
                    self.module.fail_json(msg=self.requestParse(create_project_request))

                after_request = requests.get(
                    f"{self.api_url}/projects?page=1&page_size=1&name={self.module.params['name'] }",
                    auth=self.auth
                )
                self.result['project'] = copy.deepcopy(after_request.json())
            self.result['changed'] = True

        self.module.exit_json(**self.result)

def main():
    HarborProjectModule()

if __name__ == '__main__':
    main()
