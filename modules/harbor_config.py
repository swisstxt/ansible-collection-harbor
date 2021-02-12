import copy
from ansible_collections.swisstxt.harbor.plugins.module_utils.base import HarborBaseModule
import json
import requests
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: harbor_config
author:
  - Joshua Hügli (@joschi36)
version_added: ""
short_description: Manage Harbor configuration
description:
  - Update Harbor Configuration over API.
  - Can be run wihout `configuration` to get current config.
options:
  configuration:
    description:
    - Dict with configuration options of Harbor.
    - Changes to secrets, like `oidc_client_secret`, get applied without showing a change as we do not know what the value before was.
    required: false
    type: dict
    default: {}
extends_documentation_fragment:
  - joschi36.harbor.api
'''

class HarborConfigModule(HarborBaseModule):
    @property
    def argspec(self):
        argument_spec = copy.deepcopy(self.COMMON_ARG_SPEC)
        argument_spec.update(
            configuration=dict(type='dict', required=False),
            force=dict(type='bool', required=False, default=False),
            state=dict(default='present', choices=['present'])
        )
        return argument_spec

    def __init__(self):
        self.module = AnsibleModule(
            argument_spec=self.argspec,
            supports_check_mode=True
        )

        super().__init__()

        result = dict(
            changed=False
        )

        # Get existing configuration
        before_request = requests.get(
            self.api_url+'/configurations',
            auth=self.auth
        )
        before = before_request.json()
        result['configuration'] = before.copy()

        # Check & "calculate" desired configuration
        desired_configuration = self.module.params['configuration']
        if desired_configuration:
            after_calculated = before.copy()
            for configuration in list(desired_configuration):
                if not configuration == "oidc_client_secret":
                    # Check if configuration option is available
                    if configuration not in before:
                        self.module.fail_json(msg=f"Configuration option {configuration} unavailable.", **result)

                    # Remove not changed configurations
                    if desired_configuration[configuration] == before[configuration]['value']:
                        desired_configuration.pop(configuration)
                        continue

                    # Check if configuration is editable
                    if not before[configuration]['editable']:
                        self.module.fail_json(msg=f"Configuration option {configuration} not editable.", **result)

                    # Create fake server response for diff
                    after_calculated.update({
                        configuration: {
                            "value": desired_configuration[configuration],
                            "editable": before[configuration]['editable']
                        }
                    })

            result['desired_configuration'] = desired_configuration
            if (not self.module.params['force']) and before == after_calculated:
                result['changed'] = False
                self.module.exit_json(**result)

            # Test change with checkmode
            if self.module.check_mode:
                result['changed'] = True
                result['diff'] = {
                    "before": json.dumps(before, indent=4),
                    "after": json.dumps(after_calculated, indent=4),
                }

            # Apply change without checkmode
            else:
                set_request = requests.put(
                    self.api_url+'/configurations',
                    auth=self.auth,
                    json=desired_configuration,
                )
                if set_request.status_code == 200:
                    pass
                elif set_request.status_code == 401:
                    self.module.fail_json(msg="User need to log in first.", **result)
                elif set_request.status_code == 403:
                    self.module.fail_json(msg="User does not have permission of admin role.", **result)
                elif set_request.status_code == 500:
                    self.module.fail_json(msg="Unexpected internal errors.", **result)
                else:
                    self.module.fail_json(msg=f"""
                        Unknown HTTP status code: {set_request.status_code}
                        Body: {set_request.text}
                    """)

                after_request = requests.get(
                    self.api_url+'/configurations',
                    auth=self.auth
                )
                after = after_request.json()
                result['configuration'] = after.copy()

                if before != after:
                    result['changed'] = True
                    result['diff'] = {
                        "before": json.dumps(before, indent=4),
                        "after": json.dumps(after, indent=4),
                    }

        self.module.exit_json(**result)

def main():
    HarborConfigModule()

if __name__ == '__main__':
    main()
