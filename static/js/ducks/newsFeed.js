import messageHandler from 'baselayer/MessageHandler';
import * as API from '../API';


export const FETCH_NEWSFEED = 'skyportal/FETCH_NEWSFEED';
export const FETCH_NEWSFEED_OK = 'skyportal/FETCH_NEWSFEED_OK';


export function fetchNewsFeed() {
  return API.GET('/api/newsfeed', FETCH_NEWSFEED);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_NEWSFEED) {
    dispatch(fetchNewsFeed());
  }
});

export default function reducer(state=[], action) {
  switch (action.type) {
    case FETCH_NEWSFEED_OK: {
      const newsFeedItems = action.data.news_feed_items;
      return {
        ...state,
        newsFeedItems
      };
    }
    default:
      return state;
  }
}
