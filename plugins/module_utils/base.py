from ansible.module_utils.urls import url_argument_spec
from ansible.module_utils.basic import AnsibleModule
import requests

__metaclass__ = type

class HarborBaseModule(object):
    COMMON_ARG_SPEC = dict(
        api_url=dict(type='str', required=True),
        api_username=dict(type='str', required=True),
        api_password=dict(type='str', required=True, no_log=True),
        api_verify=dict(type='bool', required=False, default=True)
    )

    def __init__(self):
        self.api_url = self.module.params['api_url']
        self.auth=(self.module.params['api_username'],self.module.params['api_password'])
        self.api_verify=self.module.params['api_verify']

    def getProjectByName(self, name):
        r = requests.get(
            f"{self.api_url}/projects?name={name}",
            auth=self.auth,
            verify=self.api_verify
        )

        try:
            project_list = r.json()
        except:
            self.module.fail_json(msg="Project request failed", **self.result)
            return False

        if not len(project_list):
            return None

        for project in project_list:
            if project['name'] == name:
                return project

        return None

    def quotaBits(self, gigabytes):
        # Convert quota from user input (GiB) to api (bits)
        bits = -1 if gigabytes == -1 else gigabytes * (1024 ** 3)
        return bits

    def requestParse(self, request):
        try:
            message = \
            f"HTTP status code: {request.status_code}\n" \
            f"Message: {request.json()['errors'][0]['message']}"

        except ValueError:
            message = \
            "Unknown Response\n" \
            f"HTTP status code: {request.status_code}\n" \
            f"Body: {request.text}"

        return message
