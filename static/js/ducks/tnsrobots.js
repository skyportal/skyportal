import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_TNSROBOTS = "skyportal/FETCH_TNSROBOTS";
const FETCH_TNSROBOTS_OK = "skyportal/FETCH_TNSROBOTS_OK";

const ADD_TNSROBOT = "skyportal/ADD_TNSROBOT";

const EDIT_TNSROBOT = "skyportal/EDIT_TNSROBOT";

const DELETE_TNSROBOT = "skyportal/DELETE_TNSROBOT";

const REFRESH_TNSROBOTS = "skyportal/REFRESH_TNSROBOTS";

// eslint-disable-next-line import/prefer-default-export
export const fetchTNSRobots = (params = {}) =>
  API.GET("/api/tns_robot", FETCH_TNSROBOTS, params);

export const addTNSRobot = (data) =>
  API.POST("/api/tns_robot", ADD_TNSROBOT, data);

export const editTNSRobot = (id, data) =>
  API.PUT(`/api/tns_robot/${id}`, EDIT_TNSROBOT, data);

export const deleteTNSRobot = (id) =>
  API.DELETE(`/api/tns_robot/${id}`, DELETE_TNSROBOT);

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_TNSROBOTS) {
    if (payload?.group_id) {
      dispatch(fetchTNSRobots({ group_id: payload.group_id }));
    } else {
      dispatch(fetchTNSRobots());
    }
  }
});

const reducer = (state = { tnsrobotList: [] }, action) => {
  switch (action.type) {
    case FETCH_TNSROBOTS_OK: {
      const tnsrobotList = action.data;
      return {
        ...state,
        tnsrobotList,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("tnsrobots", reducer);
