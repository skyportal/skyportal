import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const FETCH_NEWSFEED = "skyportal/FETCH_NEWSFEED";
const FETCH_NEWSFEED_OK = "skyportal/FETCH_NEWSFEED_OK";

export function fetchNewsFeed() {
  return API.GET("/api/newsfeed", FETCH_NEWSFEED);
}

// Websocket message handler
messageHandler.add(
  (actionType: string, _payload: any, dispatch: AppDispatch) => {
    if (actionType === FETCH_NEWSFEED) {
      dispatch(fetchNewsFeed());
    }
  },
);

const initialState: Record<string, any> = {
  items: [],
};

interface NewsFeedAction {
  type: string;
  data?: any;
}

const reducer = (
  state: Record<string, any> = initialState,
  action: NewsFeedAction,
): Record<string, any> => {
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
