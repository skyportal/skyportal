import { combineReducers } from 'redux';

import { reducer as notificationsReducer } from 'baselayer/components/Notifications';

import sourcesReducer from './ducks/fetchSources';
import sourceReducer from './ducks/source';
import plotsReducer from './ducks/fetchSourcePlots';
import groupReducer from './ducks/fetchGroup';
import groupsReducer from './ducks/groups';

import * as Action from './actions';

export function sysinfoReducer(state={}, action) {
  switch (action.type) {
    case Action.FETCH_SYSINFO_OK:
      return action.data;
    default:
      return state;
  }
}

export function usersReducer(state={}, action) {
  switch (action.type) {
    case Action.FETCH_USER_OK: {
      const { id, ...user_info } = action.data.user;
      return {
        ...state,
        [id]: user_info
      };
    }
    default:
      return state;
  }
}

export function profileReducer(state={ username: '', roles: [], acls: [], tokens: [] }, action) {
  switch (action.type) {
    case Action.FETCH_USER_PROFILE_OK:
      return action.data;
    default:
      return state;
  }
}

export function miscReducer(state={ rotateLogo: false }, action) {
  switch (action.type) {
    case Action.ROTATE_LOGO: {
      return {
        ...state,
        rotateLogo: true
      };
    }
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
  profile: profileReducer,
  plots: plotsReducer,
  misc: miscReducer,
  users: usersReducer,
  sysinfo: sysinfoReducer
});

export default root;
