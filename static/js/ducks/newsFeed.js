import * as API from '../API';


export const FETCH_NEWSFEED = 'skyportal/FETCH_NEWSFEED';
export const FETCH_NEWSFEED_OK = 'skyportal/FETCH_NEWSFEED_OK';


export function fetchNewsFeed() {
  return API.GET('/api/newsfeed', FETCH_NEWSFEED);
}

export default function reducer(state={ comments: [], sources: [], photometry: [] }, action) {
  switch (action.type) {
    case FETCH_NEWSFEED_OK: {
      const { comments, sources, photometry } = action.data;
      return {
        ...state,
        comments,
        sources,
        photometry
      };
    }
    default:
      return state;
  }
}
