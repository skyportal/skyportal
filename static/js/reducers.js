import { combineReducers } from 'redux';

import { reducer as notifications } from 'baselayer/components/Notifications';

import * as Action from './actions';

let initialState = {
  loaded: null,
  loadError: false,
  latest: []
}

export function sources(state=initialState, action) {
  switch (action.type) {
    case Action.RECEIVE_SOURCES:
      let sources = action.data;
      return {
        ...state,
        latest: sources
      }
    case Action.RECEIVE_LOADED_SOURCE:
      let source = action.data;
      return {
        ...state,
        loaded: source,
        loadError: false
      }
    case Action.RECEIVE_LOADED_SOURCE_FAIL:
      return {
        ...state,
        loadError: true
      }
    default:
      return state;
  }
}

const root = combineReducers({
  sources,
  notifications
});

export default root;
