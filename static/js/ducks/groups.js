import * as API from '../API';


export const FETCH_GROUPS = 'skyportal/FETCH_GROUPS';
export const FETCH_GROUPS_OK = 'skyportal/FETCH_GROUPS_OK';

export const ADD_GROUP = 'skyportal/ADD_GROUP';
export const ADD_GROUP_OK = 'skyportal/ADD_GROUP_OK';

export const DELETE_GROUP = 'skyportal/DELETE_GROUP';
export const DELETE_GROUP_OK = 'skyportal/DELETE_GROUP_OK';

export const ADD_GROUP_USER = 'skyportal/ADD_GROUP_USER';
export const ADD_GROUP_USER_OK = 'skyportal/ADD_GROUP_USER_OK';

export const DELETE_GROUP_USER = 'skyportal/DELETE_GROUP_USER';
export const DELETE_GROUP_USER_OK = 'skyportal/DELETE_GROUP_USER_OK';


export function fetchGroups() {
  return API.GET('/api/groups', FETCH_GROUPS);
}

export function addNewGroup(form_data) {
  return API.POST('/api/groups', ADD_GROUP, form_data);
}

export function deleteGroup(group_id) {
  return API.DELETE(`/api/groups/${group_id}`, DELETE_GROUP);
}

export function addGroupUser({ username, admin, group_id }) {
  return API.PUT(
    `/api/groups/${group_id}/users/${username}`,
    ADD_GROUP_USER,
    { username, admin, group_id }
  );
}

export function deleteGroupUser({ username, group_id }) {
  return API.DELETE(
    `/api/groups/${group_id}/users/${username}`,
    DELETE_GROUP_USER,
    { username, group_id }
  );
}


export default function reducer(state={ latest: [], all: null }, action) {
  switch (action.type) {
    case FETCH_GROUPS_OK: {
      const { user_groups, all_groups } = action.data;
      return {
        ...state,
        latest: user_groups,
        all: all_groups
      };
    }
    default:
      return state;
  }
}
