import { combineReducers } from 'redux';

import { reducer as notifications } from 'baselayer/components/Notifications';

import * as Action from './actions';

// Reducer for currently displayed source
export function source(state={ fields: null, loadError: false }, action) {
  switch (action.type) {
    case Action.RECEIVE_LOADED_SOURCE:
      let source = action.data;
      return {
        ...state,
        fields: source,
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

export function sources(state={ latest: [] }, action) {
  switch (action.type) {
    case Action.RECEIVE_SOURCES:
      let sources = action.data;
      return {
        ...state,
        latest: sources
      }
    default:
      return state;
  }
}

const root = combineReducers({
  source,
  sources,
  notifications
});

export default root;
