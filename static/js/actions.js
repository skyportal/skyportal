import * as API from './API';
import * as groupsActions from './ducks/groups';

export const ADD_GROUP = 'skyportal/ADD_GROUP';
export const ADD_GROUP_OK = 'skyportal/ADD_GROUP_OK';

export const ADD_GROUP_USER = 'skyportal/ADD_GROUP_USER';
export const ADD_GROUP_USER_OK = 'skyportal/ADD_GROUP_USER_OK';

export const DELETE_GROUP_USER = 'skyportal/DELETE_GROUP_USER';
export const DELETE_GROUP_USER_OK = 'skyportal/DELETE_GROUP_USER_OK';

export const FETCH_USER_PROFILE = 'skyportal/FETCH_USER_PROFILE';
export const FETCH_USER_PROFILE_OK = 'skyportal/FETCH_USER_PROFILE_OK';

export const FETCH_SYSINFO = 'skyportal/FETCH_SYSINFO';
export const FETCH_SYSINFO_OK = 'skyportal/FETCH_SYSINFO_OK';

export const GENERATE_TOKEN = 'skyportal/GENERATE_TOKEN';
export const GENERATE_TOKEN_OK = 'skyportal/GENERATE_TOKEN_OK';

export const DELETE_TOKEN = 'skyportal/DELETE_TOKEN';
export const DELETE_TOKEN_OK = 'skyportal/DELETE_TOKEN_OK';

export const FILTER_SOURCES = 'skyportal/FILTER_SOURCES';
export const FILTER_SOURCES_OK = 'skyportal/FILTER_SOURCES_OK';

export const FETCH_USER = 'skyportal/FETCH_USER';
export const FETCH_USER_OK = 'skyportal/FETCH_USER_OK';

export const ROTATE_LOGO = 'skyportal/ROTATE_LOGO';


export function fetchUser(id) {
  return API.GET(`/api/user/${id}`, FETCH_USER);
}

export function fetchUserProfile() {
  return API.GET('/api/internal/profile', FETCH_USER_PROFILE);
}

export function fetchSystemInfo() {
  return API.GET('/api/sysinfo', FETCH_SYSINFO);
}

export function hydrate() {
  return (dispatch) => {
    dispatch(fetchSystemInfo());
    dispatch(fetchUserProfile());
    dispatch(groupsActions.fetchGroups());
  };
}

export function rotateLogo() {
  return {
    type: ROTATE_LOGO
  };
}

export function addNewGroup(form_data) {
  return API.POST('/api/groups', ADD_GROUP, form_data);
}

export function createToken(form_data) {
  return API.POST('/api/internal/tokens', GENERATE_TOKEN, form_data);
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

export function deleteToken(tokenID) {
  console.log('called Actions.deleteToken');
  return API.DELETE(
    `/api/internal/tokens/${tokenID}`,
    DELETE_TOKEN
  );
}
