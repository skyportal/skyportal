import store from "../store";

export const TOGGLE_SIDEBAR = "skyportal/TOGGLE_SIDEBAR";

export function toggleSidebar() {
  return {
    type: TOGGLE_SIDEBAR,
  };
}

const isMobile = window.matchMedia("(max-width: 768px)").matches;
const defaultOpen = !isMobile;

const reducer = (state = { open: defaultOpen }, action) => {
  switch (action.type) {
    case TOGGLE_SIDEBAR: {
      return {
        ...state,
        open: !state.open,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sidebar", reducer);
