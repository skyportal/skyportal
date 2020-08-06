import * as API from '../API';
import store from '../store';

export const FETCH_TAXONOMIES = 'skyportal/FETCH_TAXONOMIES';
export const FETCH_TAXONOMIES_OK = 'skyportal/FETCH_TAXONOMIES_OK';

export const fetchTaxonomies = () => (
  API.GET('/api/taxonomy', FETCH_TAXONOMIES)
);

const reducer = (state={ taxonomyList: [] }, action) => {
  switch (action.type) {
    case FETCH_TAXONOMIES_OK: {
      const taxonomyList = action.data;
      return {
        ...state,
        taxonomyList
      };
    }
    default:
      return state;
  }
};

store.injectReducer('taxonomies', reducer);
