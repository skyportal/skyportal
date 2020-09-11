import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_STREAMS = "skyportal/FETCH_STREAMS";
export const FETCH_STREAMS_OK = "skyportal/FETCH_STREAMS_OK";

export const ADD_STREAM = "skyportal/ADD_STREAM";
export const ADD_STREAM_OK = "skyportal/ADD_STREAM_OK";

export const DELETE_STREAM = "skyportal/DELETE_STREAM";
export const DELETE_STREAM_OK = "skyportal/DELETE_STREAM_OK";

export const ADD_GROUP_STREAM = "skyportal/ADD_GROUP_STREAM";
export const ADD_GROUP_STREAM_OK = "skyportal/ADD_GROUP_STREAM_OK";

export const DELETE_GROUP_STREAM = "skyportal/DELETE_GROUP_STREAM";
export const DELETE_GROUP_STREAM_OK = "skyportal/DELETE_GROUP_STREAM_OK";

export function fetchStreams() {
  return API.GET("/api/streams", FETCH_STREAMS);
}

export function addNewStream(form_data) {
  return API.POST("/api/streams", ADD_STREAM, form_data);
}

export function deleteStream(stream_id) {
  return API.DELETE(`/api/streams/${stream_id}`, DELETE_STREAM);
}

export function addGroupStream({ group_id, stream_id }) {
  return API.POST(`/api/groups/${group_id}/streams`, ADD_GROUP_STREAM, {
    stream_id,
  });
}

export function deleteGroupStream({ group_id, stream_id }) {
  return API.DELETE(
    `/api/groups/${group_id}/streams/${stream_id}`,
    DELETE_GROUP_STREAM
  );
}

export function deleteUserStream({ user_id, stream_id }) {
  console.log(user_id, stream_id);
  // return API.DELETE(
  //   `/api/streams/${group_id}/streams/${stream_id}`,
  //   DELETE_GROUP_STREAM
  // );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_STREAMS) {
    dispatch(fetchStreams());
  }
});

function reducer(state = null, action) {
  switch (action.type) {
    case FETCH_STREAMS_OK: {
      return action.data;
    }
    default:
      return state;
  }
}

store.injectReducer("streams", reducer);
