import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_MOVING_OBJECT = "skyportal/REFRESH_MOVING_OBJECT";

const FETCH_MOVING_OBJECT = "skyportal/FETCH_MOVING_OBJECT";
const FETCH_MOVING_OBJECT_OK = "skyportal/FETCH_MOVING_OBJECT_OK";

const SUBMIT_MOVING_OBJECT = "skyportal/SUBMIT_MOVING_OBJECT";

const MODIFY_MOVING_OBJECT = "skyportal/MODIFY_MOVING_OBJECT";

const DELETE_MOVING_OBJECT = "skyportal/DELETE_MOVING_OBJECT";

const SUBMIT_MOVING_OBJECT_HORIZONS = "skyportal/SUBMIT_MOVING_OBJECT_HORIZONS";

const SUBMIT_MOVING_OBJECT_OBSERVATION_PLAN =
  "skyportal/SUBMIT_MOVING_OBJECT_OBSERVATION_PLAN";

export const fetchMovingObject = (id) =>
  API.GET(`/api/moving_object/${id}`, FETCH_MOVING_OBJECT);

export const submitMovingObject = (run) =>
  API.POST(`/api/moving_object`, SUBMIT_MOVING_OBJECT, run);

export const submitMovingObjectHorizons = (object_name) =>
  API.POST(`/api/moving_object/horizons`, SUBMIT_MOVING_OBJECT_HORIZONS, {
    object_name,
  });

export const modifyMovingObject = (id, params) =>
  API.PUT(`/api/moving_object/${id}`, MODIFY_MOVING_OBJECT, params);

export function deleteMovingObject(id) {
  return API.DELETE(`/api/moving_object/${id}`, DELETE_MOVING_OBJECT);
}

export const submitMovingObjectObservationPlan = (plan) =>
  API.POST(
    `/api/moving_object/observation_plan`,
    SUBMIT_MOVING_OBJECT_OBSERVATION_PLAN,
    plan,
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { moving_object } = getState();
  if (actionType === REFRESH_MOVING_OBJECT) {
    const { moving_object_id } = payload;
    if (parseInt(moving_object_id, 10) === moving_object?.id) {
      dispatch(fetchMovingObject(moving_object_id));
    }
  }
});

const reducer = (state = { assignments: [] }, action) => {
  switch (action.type) {
    case FETCH_MOVING_OBJECT_OK: {
      const moving_object = action.data;
      return {
        ...state,
        ...moving_object,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("moving_object", reducer);
