import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch, RootState } from "../types/store";

const REFRESH_STREAM = "skyportal/REFRESH_STREAM";

const FETCH_STREAM = "skyportal/FETCH_STREAM";
const FETCH_STREAM_OK = "skyportal/FETCH_STREAM_OK";
const FETCH_STREAM_ERROR = "skyportal/FETCH_STREAM_ERROR";
const FETCH_STREAM_FAIL = "skyportal/FETCH_STREAM_FAIL";

export function fetchStream(id: number | string) {
  return API.GET(`/api/streams/${id}`, FETCH_STREAM);
}

// Websocket message handler
messageHandler.add(
  (
    actionType: string,
    payload: any,
    dispatch: AppDispatch,
    getState: () => RootState,
  ) => {
    const { stream } = getState();

    if (actionType === REFRESH_STREAM) {
      const loaded_stream_id = stream ? stream.id : null;

      if (loaded_stream_id === payload.stream_id) {
        dispatch(fetchStream(loaded_stream_id));
      }
    }
  },
);

type StreamState = Record<string, any>;

interface StreamAction {
  type: string;
  data?: any;
}

const reducer = (
  state: StreamState = {},
  action: StreamAction,
): StreamState => {
  switch (action.type) {
    case FETCH_STREAM_OK: {
      return action.data;
    }
    case FETCH_STREAM_FAIL:
    case FETCH_STREAM_ERROR: {
      return {};
    }
    default:
      return state;
  }
};

store.injectReducer("stream", reducer);
