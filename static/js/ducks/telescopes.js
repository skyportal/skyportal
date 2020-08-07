import * as API from '../API';
import store from '../store';

export const FETCH_TELESCOPES = 'skyportal/FETCH_TELESCOPES';
export const FETCH_TELESCOPES_OK = 'skyportal/FETCH_TELESCOPES_OK';

export const fetchTelescopes = () => (
  API.GET('/api/telescope', FETCH_TELESCOPES)
);


const reducer = (state={ telescopeList: [] }, action) => {
  switch (action.type) {
    case FETCH_TELESCOPES_OK: {
      const telescopes = action.data;
      return {
        ...state,
        telescopeList: telescopes
      };
    }
    default:
      return state;
  }
};

store.injectReducer('telescopes', reducer);
