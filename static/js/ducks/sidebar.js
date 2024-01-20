import store from "../store";

const TOGGLE_SIDEBAR = "skyportal/TOGGLE_SIDEBAR";
const SET_SIDEBAR = "skyportal/SET_SIDEBAR";

export function toggleSidebar() {
  return {
    type: TOGGLE_SIDEBAR,
  };
}

export function setSidebar(open) {
  return {
    type: SET_SIDEBAR,
    open,
  };
}

const reducer = (state = { open: false }, action) => {
  switch (action.type) {
    case TOGGLE_SIDEBAR: {
      return {
        ...state,
        open: !state.open,
      };
    }
    case SET_SIDEBAR: {
      return {
        ...state,
        open: action.open,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sidebar", reducer);
