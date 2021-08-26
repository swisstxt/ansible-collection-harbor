#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2021, Joshua Hügli <@joschi36>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: harbor_garbase_collection
author:
  - Joshua Hügli (@joschi36)
version_added: ""
short_description: Manages Harbor garbage collection settings
description:
  - Update Harbor garbage collection options over API.

extends_documentation_fragment:
  - joschi36.harbor.api
'''

import copy
import json

import requests
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.swisstxt.harbor.plugins.module_utils.base import \
    HarborBaseModule


class HarborGarbageCollectionModule(HarborBaseModule):
    def getGarbageCollection(self):
        gc_request = requests.get(
            f"{self.api_url}/system/gc/schedule",
            auth=self.auth
        )
        if(gc_request.status_code == 200 and gc_request.headers["content-length"] == "0"):
            return {}

        gc = gc_request.json()

        job_parameters = json.loads(gc['job_parameters'])

        return {
            "parameters": {
                "delete_untagged": job_parameters['delete_untagged']
            },
            "schedule": gc['schedule']
        }

    def putGarbageCollection(self, payload):
        put_gc_request = requests.put(
            f"{self.api_url}/system/gc/schedule",
            auth=self.auth,
            json=payload
        )
        if not put_gc_request.status_code == 200:
            self.module.fail_json(msg=self.requestParse(put_gc_request))

    def constructDesired(self, delete_untagged, schedule_cron):
        return {
            "parameters": {
                "delete_untagged": delete_untagged
            },
            "schedule": {
                "cron": schedule_cron,
                "type": "Custom"
            }
        }


    @property
    def argspec(self):
        argument_spec = copy.deepcopy(self.COMMON_ARG_SPEC)
        argument_spec.update(
            schedule_cron=dict(type='str', required=True),
            delete_untagged=dict(type='bool', required=True),
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

        desired = self.constructDesired(self.module.params["delete_untagged"], self.module.params["schedule_cron"])
        before = self.getGarbageCollection()

        if desired != before:
            # Test change with checkmode
            if self.module.check_mode:
                self.result['changed'] = True
                self.result['diff'] = {
                    "before": json.dumps(before, indent=4),
                    "after": json.dumps(desired, indent=4),
                }

            # Apply change without checkmode
            else:
                self.putGarbageCollection(desired)

                after = self.getGarbageCollection()

                self.result['changed'] = True
                self.result['diff'] = {
                    "before": json.dumps(before, indent=4),
                    "after": json.dumps(after, indent=4),
                }

        self.module.exit_json(**self.result)



def main():
    HarborGarbageCollectionModule()

if __name__ == '__main__':
    main()
