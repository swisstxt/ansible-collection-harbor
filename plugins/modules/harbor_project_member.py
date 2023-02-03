#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2021, Joshua Hügli <@joschi36>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: harbor_project_member
author:
  - Joshua Hügli (@joschi36)
version_added: ""
short_description: Manage Harbor project members
description:
  - Create, update and delete Harbor project members over API.
options:
  #TODO
extends_documentation_fragment:
  - swisstxt.harbor.api
'''

import copy
import requests
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.swisstxt.harbor.plugins.module_utils.base import \
    HarborBaseModule


class HarborProjectMemberModule(HarborBaseModule):
    ROLES = {
        'projectAdmin': 1,
        'developer': 2,
        'guest': 3,
        'maintainer': 4,
        'limitedGuest': 5
    }

    @property
    def group_type_id(self):
        group_type = self.module.params['group_type']
        groups = {
            'ldap': 1,
            'http': 2,
            'oidc': 3
        }
        return groups.get(group_type)

    @property
    def role_id(self):
        role = self.module.params['role']
        roles = self.ROLES
        return roles.get(role)

    @property
    def isUser(self):
        return self.module.params['user'] is not None

    @property
    def isGroup(self):
        return self.module.params['group'] is not None

    def getMemberType(self):
        if self.isUser:
            return 'u'
        elif self.isGroup:
            return 'g'

    def getMemberName(self):
        if self.isUser:
            return self.module.params['user']
        elif self.isGroup:
            return self.module.params['group']

    def listProjectMembers(self, project_id):
        member_list_request = requests.get(
            f"{self.api_url}/projects/{project_id}/members",
            auth=self.auth
        )
        member_list = member_list_request.json()
        self.result['member_list'] = member_list
        return member_list

    def getMember(self, project_id, member_name, member_type):
        member_list = self.listProjectMembers(project_id)
        for member in member_list:
            if member['entity_type'] == member_type and member['entity_name'] == member_name:
                self.result['member'] = copy.deepcopy(member)
                return member

        return None

    @property
    def argspec(self):
        argument_spec = copy.deepcopy(self.COMMON_ARG_SPEC)
        argument_spec.update(
            project=dict(type='str', required=True),
            user=dict(type='str', required=False),
            group=dict(type='str', required=False),
            group_type=dict(
                type='str',
                required=False,
                choices=['ldap', 'http', 'oidc']
            ),
            ldap_group_dn=dict(type='str', required=False),
            role=dict(
                type='str',
                required=False,
                choices=['projectAdmin', 'maintainer', 'developer', 'guest', 'limitedGuest']
            ),

            state=dict(default='present', choices=['present', 'absent'])
        )
        return argument_spec


    def __init__(self):
        self.module = AnsibleModule(
            argument_spec=self.argspec,
            supports_check_mode=True,
            mutually_exclusive=[
                ('user', 'group')
            ],
            required_if=[
                ('group_type', 'ldap', ('ldap_group_dn'))
            ],
            required_by={
                'user': ('role'),
                'group': ('role', ('group_type'))
            }
        )

        super().__init__()

        self.result = dict(
            changed=False
        )

        # Get Project ID
        project = self.getProjectByName(self.module.params['project'])
        if not project:
            self.module.fail_json(msg="Project not found", **self.result)
        project_id = project['project_id']

        # If no user and group is given, exit with project member list
        if not self.isUser and not self.isGroup:
            self.listProjectMembers(project_id)
            self.module.exit_json(**self.result)

        member_type = self.getMemberType()
        member_name = self.getMemberName()
        member = self.getMember(
            project_id,
            member_name,
            member_type,
        )
        state = self.module.params['state']

        # Existing member, state present, modify
        if member and state == "present":
            if member["role_id"] != self.role_id:
                if not self.module.check_mode:
                    put_project_member_request = requests.put(
                        f"{self.api_url}/projects/{project_id}/members/{member['id']}",
                        json={
                            "role_id": self.role_id
                        }
                    )
                    if not put_project_member_request.status_code == 200:
                        self.module.fail_json(msg=self.requestParse(put_project_member_request))

                    # Execute getMember to set results
                    self.getMember(
                        project_id,
                        member_name,
                        member_type,
                    )

                self.result['changed'] = True

        # Existing member, state absent, delete
        elif member and state == "absent":
            if not self.module.check_mode:
                delete_project_member_request = requests.delete(
                    f"{self.api_url}/projects/{project_id}/members/{member['id']}",
                )
                if not delete_project_member_request.status_code == 200:
                    self.module.fail_json(msg=self.requestParse(delete_project_member_request))

            self.result['changed'] = True

        # Inexistent member, state present, create
        elif not member and state == "present":
            create_payload = {
                "role_id": self.role_id,
            }

            if self.isGroup:
                create_payload["member_group"] = {
                    "group_name": self.module.params['group'],
                    "group_type": self.group_type_id,
                }
                if self.module.params['ldap_group_dn'] is not None:
                    create_payload["member_group"]["ldap_group_dn"] = self.module.params['ldap_group_dn']

            if self.isUser:
                create_payload["member_user"] = {
                    "username": self.module.params['user'],
                }

            if not self.module.check_mode:
                create_project_member_request = requests.post(
                    f"{self.api_url}/projects/{project_id}/members",
                    auth=self.auth,
                    json=create_payload
                )

                if not create_project_member_request.status_code == 201:
                    self.module.fail_json(msg=self.requestParse(create_project_member_request))

                # Execute getMember to set results
                self.getMember(
                    project_id,
                    member_name,
                    member_type,
                )

            self.result['changed'] = True

        # Inexistent member, state absent, no action (just for refrence)
        else:
            pass


        self.module.exit_json(**self.result)


def main():
    HarborProjectMemberModule()

if __name__ == '__main__':
    main()
