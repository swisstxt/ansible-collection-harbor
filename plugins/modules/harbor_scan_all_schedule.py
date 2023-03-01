#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2021, Joshua Hügli <@joschi36>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: harbor_scan_all_collection
author:
  - Joshua Hügli (@joschi36)
version_added: ""
short_description: Manages Harbor scan all settings
description:
  - Update Harbor scan all options over API.

extends_documentation_fragment:
  - swisstxt.harbor.api
'''

import copy
import json

import requests
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.swisstxt.harbor.plugins.module_utils.base import \
    HarborBaseModule


class HarborScanAllScheduleModule(HarborBaseModule):
    def getSchedule(self):
        schedule_request = requests.get(
            f"{self.api_url}/system/scanAll/schedule",
            auth=self.auth,
            verify=self.api_verify
        )

        if(schedule_request.status_code == 200 and schedule_request.headers["content-length"] == "0"):
            return {}

        schedule = schedule_request.json()
        del schedule["schedule"]["next_scheduled_time"]
        return {
            "schedule": schedule['schedule']
        }

    def putSchedule(self, payload):
        put_schedule_request = requests.put(
            f"{self.api_url}/system/scanAll/schedule",
            auth=self.auth,
            json=payload,
            verify=self.api_verify
        )
        if not put_schedule_request.status_code == 200:
            self.module.fail_json(msg=self.requestParse(put_schedule_request))

    def constructDesired(self, schedule_cron):
        return {
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

        desired = self.constructDesired(self.module.params["schedule_cron"])
        before = self.getSchedule()

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
                self.putSchedule(desired)

                after = self.getSchedule()

                self.result['changed'] = True
                self.result['diff'] = {
                    "before": json.dumps(before, indent=4),
                    "after": json.dumps(after, indent=4),
                }

        self.module.exit_json(**self.result)



def main():
    HarborScanAllScheduleModule()

if __name__ == '__main__':
    main()
