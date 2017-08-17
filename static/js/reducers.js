import { combineReducers } from 'redux';

import { reducer as notificationsReducer } from 'baselayer/components/Notifications';

import * as Action from './actions';

// Reducer for currently displayed source
export function sourceReducer(state={ source: null, loadError: false }, action) {
  switch (action.type) {
    case Action.FETCH_LOADED_SOURCE_OK: {
      const source = action.data;
      return {
        ...state,
        ...source,
        loadError: false
      };
    }
    case Action.FETCH_LOADED_SOURCE_FAIL:
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
    case Action.FETCH_SOURCES_OK: {
      const sources = action.data;
      return {
        ...state,
        latest: sources
      };
    }
    default:
      return state;
  }
}

export function groupReducer(state={}, action) {
  switch (action.type) {
    case Action.FETCH_GROUP_OK:
      return action.data;
    default:
      return state;
  }
}

export function groupsReducer(state={ latest: [] }, action) {
  switch (action.type) {
    case Action.FETCH_GROUPS_OK: {
      const groups = action.data;
      return {
        ...state,
        latest: groups
      };
    }
    default:
      return state;
  }
}

export function profileReducer(state={ username: '' }, action) {
  switch (action.type) {
    case Action.FETCH_USER_PROFILE_OK:
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
