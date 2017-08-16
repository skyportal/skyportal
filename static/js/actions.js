export const FETCH_SOURCES = 'skyportal/FETCH_SOURCES';
export const FETCH_SOURCES_OK = 'skyportal/FETCH_SOURCES_OK';

export const REFRESH_SOURCE = 'skyportal/REFRESH_SOURCE';

export const FETCH_LOADED_SOURCE = 'skyportal/FETCH_LOADED_SOURCE';
export const FETCH_LOADED_SOURCE_OK = 'skyportal/FETCH_LOADED_SOURCE_OK';
export const FETCH_LOADED_SOURCE_FAIL = 'skyportal/FETCH_LOADED_SOURCE_FAIL';

export const FETCH_SOURCE_PLOT = 'skyportal/FETCH_SOURCE_PLOT';
export const FETCH_SOURCE_PLOT_OK = 'skyportal/FETCH_SOURCE_PLOT_OK';
export const FETCH_SOURCE_PLOT_FAIL = 'skyportal/FETCH_SOURCE_PLOT_FAIL';

export const FETCH_GROUPS = 'skyportal/FETCH_GROUPS';
export const FETCH_GROUPS_OK = 'skyportal/FETCH_GROUPS_OK';

export const FETCH_GROUP = 'skyportal/FETCH_GROUP';
export const FETCH_GROUP_OK = 'skyportal/FETCH_GROUP_OK';

export const ADD_COMMENT = 'skyportal/ADD_COMMENT';
export const ADD_COMMENT_OK = 'skyportal/ADD_COMMENT_OK';

export const FETCH_USER_PROFILE = 'skyportal/FETCH_USER_PROFILE';
export const FETCH_USER_PROFILE_OK = 'skyportal/FETCH_USER_PROFILE_OK';


import * as API from './API';


export function fetchSource(id) {
  return API.GET(`/api/sources/${id}`, FETCH_LOADED_SOURCE);
}

export function fetchSources() {
  return API.GET('/api/sources', FETCH_SOURCES);
}

export function fetchGroup(id) {
  return API.GET(`/api/groups/${id}`, FETCH_GROUP);
}

export function fetchGroups() {
  return API.GET('/api/groups', FETCH_GROUPS);
}

export function fetchUserProfile() {
  return API.GET('/api/profile', FETCH_USER_PROFILE);
}

export function hydrate() {
  return (dispatch) => {
    dispatch(fetchUserProfile());
    dispatch(fetchSources());
    dispatch(fetchGroups());
  };
}

export function addComment({source_id, text}) {
  return API.POST(`/api/comment`, ADD_COMMENT, {source_id, text});
}
