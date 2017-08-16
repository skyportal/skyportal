import { combineReducers } from 'redux';

import { reducer as notificationsReducer } from 'baselayer/components/Notifications';

import * as Action from './actions';

// Reducer for currently displayed source
export function sourceReducer(state={ source: null, loadError: false }, action) {
  switch (action.type) {
    case Action.RECEIVE_LOADED_SOURCE:
      let source = action.data;
      return {
        ...state,
        ...source,
        loadError: false
      };
    case Action.RECEIVE_LOADED_SOURCE_FAIL:
      return {
        ...state,
        loadError: true
      };
    default:
      return state;
  }
}

export function sourcesReducer(state={ latest: [] }, action) {
  switch (action.type) {
    case Action.RECEIVE_SOURCES:
      let sources = action.data;
      return {
        ...state,
        latest: sources
      };
    default:
      return state;
  }
}

export function groupReducer(state={}, action) {
  switch (action.type) {
    case Action.RECEIVE_GROUP:
      return action.data;
    default:
      return state;
  }
}

export function groupsReducer(state={ latest: [] }, action) {
  switch (action.type) {
    case Action.RECEIVE_GROUPS:
      let groups = action.data;
      return {
        ...state,
        latest: groups
      };
    default:
      return state;
  }
}

export function profileReducer(state={ username: '' }, action) {
  switch (action.type) {
    case Action.RECEIVE_USER_PROFILE:
      return action.data;
    default:
      return state;
    }
}

const root = combineReducers({
  source: sourceReducer,
  sources: sourcesReducer,
  group: groupReducer,
  groups: groupsReducer,
  notifications: notificationsReducer,
  profile: profileReducer
});

export default root;
