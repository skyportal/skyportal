import store from "../store";

const TOGGLE_SIDEBAR = "skyportal/TOGGLE_SIDEBAR";
const SET_SIDEBAR = "skyportal/SET_SIDEBAR";

export function toggleSidebar() {
  return {
    type: TOGGLE_SIDEBAR,
  };
}

export function setSidebar(open: boolean) {
  return {
    type: SET_SIDEBAR,
    open,
  };
}

const reducer = (
  state: { open: boolean } = { open: false },
  action: { type: string; open?: boolean },
): { open: boolean } => {
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
        open: action.open ?? state.open,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sidebar", reducer);
