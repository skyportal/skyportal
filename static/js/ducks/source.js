import messageHandler from 'baselayer/MessageHandler';

import * as API from '../API';
import store from '../store';


export const REFRESH_SOURCE = 'skyportal/REFRESH_SOURCE';

export const FETCH_LOADED_SOURCE = 'skyportal/FETCH_LOADED_SOURCE';
export const FETCH_LOADED_SOURCE_OK = 'skyportal/FETCH_LOADED_SOURCE_OK';
export const FETCH_LOADED_SOURCE_ERROR = 'skyportal/FETCH_LOADED_SOURCE_ERROR';
export const FETCH_LOADED_SOURCE_FAIL = 'skyportal/FETCH_LOADED_SOURCE_FAIL';

export const ADD_COMMENT = 'skyportal/ADD_COMMENT';
export const ADD_COMMENT_OK = 'skyportal/ADD_COMMENT_OK';

export const DELETE_COMMENT = 'skyportal/DELETE_COMMENT';
export const DELETE_COMMENT_OK = 'skyportal/DELETE_COMMENT_OK';

export const ADD_SOURCE_VIEW = 'skyportal/ADD_SOURCE_VIEW';
export const ADD_SOURCE_VIEW_OK = 'skyportal/ADD_SOURCE_VIEW_OK';

export const SUBMIT_FOLLOWUP_REQUEST = 'skyportal/SUBMIT_FOLLOWUP_REQUEST';
export const SUBMIT_FOLLOWUP_REQUEST_OK = 'skyportal/SUBMIT_FOLLOWUP_REQUEST_OK';

export const EDIT_FOLLOWUP_REQUEST = 'skyportal/EDIT_FOLLOWUP_REQUEST';
export const EDIT_FOLLOWUP_REQUEST_OK = 'skyportal/EDIT_FOLLOWUP_REQUEST_OK';

export const DELETE_FOLLOWUP_REQUEST = 'skyportal/DELETE_FOLLOWUP_REQUEST';
export const DELETE_FOLLOWUP_REQUEST_OK = 'skyportal/DELETE_FOLLOWUP_REQUEST_OK';

export function addComment(form) {
  function fileReaderPromise(file) {
    return new Promise((resolve) => {
      const filereader = new FileReader();
      filereader.readAsDataURL(file);
      filereader.onloadend = () => resolve(
        { body: filereader.result, name: file.name }
      );
    });
  }
  if (form.attachment) {
    return (dispatch) => {
      fileReaderPromise(form.attachment)
        .then((fileData) => {
          form.attachment = fileData;
          dispatch(API.POST(`/api/comment`, ADD_COMMENT, form));
        });
    };
  } else {
    return API.POST(`/api/comment`, ADD_COMMENT, form);
  }
}

export function deleteComment(comment_id) {
  return API.DELETE(`/api/comment/${comment_id}`, DELETE_COMMENT);
}

export function fetchSource(id) {
  return API.GET(`/api/sources/${id}`, FETCH_LOADED_SOURCE);
}

export function addSourceView(id) {
  return API.POST(`/api/internal/source_views/${id}`, ADD_SOURCE_VIEW);
}

export const submitFollowupRequest = (params) => {
  const { instrument_name, ...paramsToSubmit } = params;
  return API.POST('/api/followup_request', SUBMIT_FOLLOWUP_REQUEST, paramsToSubmit);
};

export const editFollowupRequest = (params, requestID) => {
  const { instrument_name, ...paramsToSubmit } = params;
  return API.PUT(`/api/followup_request/${requestID}`, EDIT_FOLLOWUP_REQUEST, paramsToSubmit);
};

export const deleteFollowupRequest = (id) => (
  API.DELETE(`/api/followup_request/${id}`, DELETE_FOLLOWUP_REQUEST)
);


// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { source } = getState();

  if (actionType === REFRESH_SOURCE) {
    const loaded_source_id = source ? source.id : null;

    if (loaded_source_id === payload.source_id) {
      dispatch(fetchSource(loaded_source_id));
    }
  }
});


// Reducer for currently displayed source
const reducer = (state={ source: null, loadError: false }, action) => {
  switch (action.type) {
    case FETCH_LOADED_SOURCE_OK: {
      const source = action.data.sources;
      return {
        ...state,
        ...source,
        loadError: ""
      };
    }
    case FETCH_LOADED_SOURCE_ERROR:
      return {
        ...state,
        loadError: action.message
      };

    case FETCH_LOADED_SOURCE_FAIL:
      return {
        ...state,
        loadError: "Unknown error while loading source"
      };
    default:
      return state;
  }
};

store.injectReducer('source', reducer);
