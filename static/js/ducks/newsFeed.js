import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_NEWSFEED = "skyportal/FETCH_NEWSFEED";
export const FETCH_NEWSFEED_OK = "skyportal/FETCH_NEWSFEED_OK";

export function fetchNewsFeed() {
  return API.GET("/api/newsfeed", FETCH_NEWSFEED);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_NEWSFEED) {
    dispatch(fetchNewsFeed());
  }
});

const initialState = {
  items: [],
};

const reducer = (state = initialState, action) => {
  switch (action.type) {
    case FETCH_NEWSFEED_OK: {
      const newsFeedItems = action.data;
      return {
        ...state,
        items: newsFeedItems,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("newsFeed", reducer);
