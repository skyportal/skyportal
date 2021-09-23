import messageHandler from "baselayer/MessageHandler";
import * as API from "../API";
import store from "../store";

const FETCH_REJECTED_CANDIDATES = "skyportal/FETCH_REJECTED_CANDIDATES";
const FETCH_REJECTED_CANDIDATES_OK = "skyportal/FETCH_REJECTED_CANDIDATES_OK";
const ADD_TO_REJECTED_CANDIDATES = "skyportal/ADD_TO_REJECTED_CANDIDATES";
const REMOVE_FROM_REJECTED_CANDIDATES =
  "skyportal/REMOVE_FROM_REJECTED_CANDIDATES";
const REFRESH_REJECTED_CANDIDATES = "skyportal/REFRESH_REJECTED_CANDIDATES";

// eslint-disable-next-line import/prefer-default-export
export const fetchRejected = () =>
  API.GET("/api/listing", FETCH_REJECTED_CANDIDATES, {
    listName: "rejected_candidates",
  });

export const addToRejected = (obj_id) =>
  API.POST("/api/listing", ADD_TO_REJECTED_CANDIDATES, {
    list_name: "rejected_candidates",
    obj_id,
  });

export const removeFromRejected = (obj_id) =>
  API.DELETE("/api/listing", REMOVE_FROM_REJECTED_CANDIDATES, {
    list_name: "rejected_candidates",
    obj_id,
  });

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_REJECTED_CANDIDATES) {
    dispatch(fetchRejected());
  }
});

const reducer = (state = { rejected_candidates: [] }, action) => {
  switch (action.type) {
    case FETCH_REJECTED_CANDIDATES_OK: {
      const rejected_candidates = action.data?.map((rej) => rej.obj_id);
      return {
        ...state,
        rejected_candidates,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("rejected_candidates", reducer);
