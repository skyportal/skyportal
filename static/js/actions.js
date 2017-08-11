export const RECEIVE_SOURCES = 'skyportal/RECEIVE_SOURCES';
export const RECEIVE_LOADED_SOURCE = 'skyportal/RECEIVE_LOADED_SOURCE';
export const RECEIVE_LOADED_SOURCE_FAIL = 'skyportal/RECEIVE_LOADED_SOURCE_FAIL';
export const RECEIVE_SOURCE_PLOT = 'skyportal/RECEIVE_SOURCE_PLOT';
export const RECEIVE_SOURCE_PLOT_FAIL = 'skyportal/RECEIVE_SOURCE_PLOT_FAIL';
export const ADD_COMMENT = 'skyportal/ADD_COMMENT';
export const FETCH_COMMENTS = 'skyportal/FETCH_COMMENTS';
export const RECEIVE_COMMENTS = 'skyportal/RECEIVE_COMMENTS';
export const RECEIVE_COMMENTS_FAIL = 'skyportal/RECEIVE_COMMENTS_FAIL';
export const RECEIVE_USER_PROFILE = 'skyportal/RECEIVE_USER_PROFILE';


import * as API from './API';


export function fetchSource(id) {
  return API.GET(`/sources/${id}`, RECEIVE_LOADED_SOURCE);
}

export function fetchSources() {
  return API.GET('/sources', RECEIVE_SOURCES);
}

export function fetchComments(source) {
  return API.GET(`/source/${source}/comments`, RECEIVE_COMMENTS);
}

export function fetchUserProfile() {
  return API.GET('/profile', RECEIVE_USER_PROFILE);
}

export function hydrate() {
  return (dispatch) => {
    dispatch(fetchUserProfile());
    dispatch(fetchSources());
  };
}

export function addComment(source_id, text) {
  return API.POST(`/comment`, ADD_COMMENT, {source_id, text});
}
