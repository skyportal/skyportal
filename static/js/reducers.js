import { combineReducers } from 'redux';

import { reducer as notificationsReducer } from 'baselayer/components/Notifications';

import * as Action from './actions';

// Reducer for currently displayed source
export function sourceReducer(state={ fields: null, loadError: false }, action) {
  switch (action.type) {
    case Action.RECEIVE_LOADED_SOURCE:
      let source = action.data;
      return {
        ...state,
        fields: source,
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

export function commentsReducer(state={}, action) {
  switch (action.type) {

  case Action.RECEIVE_COMMENTS:
    let comments = action.data || [];
    if (comments.length > 0) {
      let source_id = comments[0].source_id;
      comments = comments.filter(comment => comment.source_id == source_id);
      return {
        ...state,
        [source_id]: comments
      };
    } else {
      return state;
    }
  default:
    return state;

  }
}

const root = combineReducers({
  comments: commentsReducer,
  source: sourceReducer,
  sources: sourcesReducer,
  notifications: notificationsReducer
});

export default root;
