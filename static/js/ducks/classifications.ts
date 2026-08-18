import store from "../store";

const SET_TAXONOMY = "skyportal/SET_TAXONOMY";
const SET_SCALE_PROBABILITIES = "skyportal/SET_SCALE_PROBABILITIES";
const SET_UPDATE_EXISTING = "skyportal/SET_UPDATE_EXISTING";

export const setTaxonomy = (taxonomy: any) => ({
  type: SET_TAXONOMY,
  taxonomy,
});

export const setScaleProbabilities = (scaleProbabilities: any) => ({
  type: SET_SCALE_PROBABILITIES,
  scaleProbabilities,
});

export const setUpdateExisting = (updateExisting: any) => ({
  type: SET_UPDATE_EXISTING,
  updateExisting,
});

interface ClassificationsAction {
  type: string;
  taxonomy?: any;
  scaleProbabilities?: any;
  updateExisting?: any;
  [key: string]: any;
}

const reducer = (
  state: Record<string, any> = { rotateLogo: false, updateExisting: true },
  action: ClassificationsAction,
): Record<string, any> => {
  switch (action.type) {
    case SET_TAXONOMY: {
      const { taxonomy } = action;
      return {
        ...state,
        taxonomy,
      };
    }
    case SET_SCALE_PROBABILITIES: {
      const { scaleProbabilities } = action;
      return {
        ...state,
        scaleProbabilities,
      };
    }
    case SET_UPDATE_EXISTING: {
      const { updateExisting } = action;
      return {
        ...state,
        updateExisting,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("classifications", reducer);
