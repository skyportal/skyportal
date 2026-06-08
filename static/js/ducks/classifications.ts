import store from "../store";

const SET_TAXONOMY = "skyportal/SET_TAXONOMY";
const SET_SCALE_PROBABILITIES = "skyportal/SET_SCALE_PROBABILITIES";

export const setTaxonomy = (taxonomy: any) => ({
  type: SET_TAXONOMY,
  taxonomy,
});

export const setScaleProbabilities = (scaleProbabilities: any) => ({
  type: SET_SCALE_PROBABILITIES,
  scaleProbabilities,
});

interface ClassificationsAction {
  type: string;
  taxonomy?: any;
  scaleProbabilities?: any;
  [key: string]: any;
}

const reducer = (
  state: Record<string, any> = { rotateLogo: false },
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
    default:
      return state;
  }
};

store.injectReducer("classifications", reducer);
