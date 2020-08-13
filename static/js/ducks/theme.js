import store from "../store";

export const UPDATE_MATERIAL_THEME = "skyportal/UPDATE_MATERIAL_THEME";

export function updateMaterialTheme(theme) {
  return {
    type: UPDATE_MATERIAL_THEME,
    theme,
  };
}

const initialState = {
  profile: {
    preferences: {
      theme: "light",
    },
  },
};

const reducer = (state = initialState, action) => {
  switch (action.type) {
    case UPDATE_MATERIAL_THEME: {
      const { theme } = action;
      return {
        ...state,
        profile: {
          ...state.profile,
          preferences: {
            ...state.profile.preferences,
            theme,
          },
        },
      };
    }
    default:
      return state;
  }
};

store.injectReducer("theme", reducer);
