import store from '../store';

export const TOGGLE_SIDEBAR = 'skyportal/TOGGLE_SIDEBAR';

export function toggleSidebar() {
  return {
    type: TOGGLE_SIDEBAR
  };
}

// TODO Set open to false by default on mobile
const reducer = (state={ open: true }, action) => {
  switch (action.type) {
    case TOGGLE_SIDEBAR: {
      return {
        ...state,
        open: !state.open
      };
    }
    default:
      return state;
  }
};

store.injectReducer('sidebar', reducer);
