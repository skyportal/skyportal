import messageHandler from 'baselayer/MessageHandler';

import * as API from '../API';
import store from '../store';

export const FETCH_TOP_EVENTS = 'skyportal/FETCH_TOP_EVENTS';
export const FETCH_TOP_EVENTS_OK = 'skyportal/FETCH_TOP_EVENTS_OK';

export const fetchTopEvents = () => (
  API.GET('/api/internal/event_views', FETCH_TOP_EVENTS)
);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_TOP_EVENTS) {
    dispatch(fetchTopEvents());
  }
});

const reducer = (state={ eventViews: [] }, action) => {
  switch (action.type) {
    case FETCH_TOP_EVENTS_OK: {
      const eventViews = action.data;
      return {
        eventViews
      };
    }
    default:
      return state;
  }
};

store.injectReducer('topEvents', reducer);
