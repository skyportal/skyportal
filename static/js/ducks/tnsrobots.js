import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_TNSROBOTS = "skyportal/FETCH_TNSROBOTS";
const FETCH_TNSROBOTS_OK = "skyportal/FETCH_TNSROBOTS_OK";

const ADD_TNSROBOT = "skyportal/ADD_TNSROBOT";
const EDIT_TNSROBOT = "skyportal/EDIT_TNSROBOT";
const DELETE_TNSROBOT = "skyportal/DELETE_TNSROBOT";
const REFRESH_TNSROBOTS = "skyportal/REFRESH_TNSROBOTS";

const ADD_TNSROBOT_GROUP = "skyportal/ADD_TNSROBOT_GROUP";
const EDIT_TNSROBOT_GROUP = "skyportal/EDIT_TNSROBOT_GROUP";
const DELETE_TNSROBOT_GROUP = "skyportal/DELETE_TNSROBOT_GROUP";

const ADD_TNSROBOT_GROUP_AUTOREPORTER =
  "skyportal/ADD_TNSROBOT_GROUP_AUTOREPORTER";
const DELETE_TNSROBOT_GROUP_AUTOREPORTER =
  "skyportal/DELETE_TNSROBOT_GROUP_AUTOREPORTER";

const ADD_TNSROBOT_COAUTHOR = "skyportal/ADD_TNSROBOT_COAUTHOR";
const DELETE_TNSROBOT_COAUTHOR = "skyportal/DELETE_TNSROBOT_COAUTHOR";

const FETCH_TNSROBOT_SUBMISSIONS = "skyportal/FETCH_TNSROBOT_SUBMISSIONS";
const FETCH_TNSROBOT_SUBMISSIONS_OK = "skyportal/FETCH_TNSROBOT_SUBMISSIONS_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchTNSRobots = (params = {}) =>
  API.GET("/api/tns_robot", FETCH_TNSROBOTS, params);

export const addTNSRobot = (data) =>
  API.PUT("/api/tns_robot", ADD_TNSROBOT, data);

export const editTNSRobot = (id, data) =>
  API.PUT(`/api/tns_robot/${id}`, EDIT_TNSROBOT, data);

export const deleteTNSRobot = (id) =>
  API.DELETE(`/api/tns_robot/${id}`, DELETE_TNSROBOT);

export const addTNSRobotGroup = (tnsrobot_id, data) =>
  API.PUT(`/api/tns_robot/${tnsrobot_id}/group`, ADD_TNSROBOT_GROUP, data);

export const editTNSRobotGroup = (tnsrobot_id, group_id, data) =>
  API.PUT(
    `/api/tns_robot/${tnsrobot_id}/group/${group_id}`,
    EDIT_TNSROBOT_GROUP,
    data,
  );

export const deleteTNSRobotGroup = (tnsrobot_id, group_id) =>
  API.DELETE(
    `/api/tns_robot/${tnsrobot_id}/group/${group_id}`,
    DELETE_TNSROBOT_GROUP,
  );

export const addTNSRobotGroupAutoReporters = (
  tnsrobot_id,
  group_id,
  user_ids = [],
) =>
  API.POST(
    `/api/tns_robot/${tnsrobot_id}/group/${group_id}/autoreporter`,
    ADD_TNSROBOT_GROUP_AUTOREPORTER,
    { user_ids },
  );

export const deleteTNSRobotGroupAutoReporters = (
  tnsrobot_id,
  group_id,
  user_ids = [],
) =>
  API.DELETE(
    `/api/tns_robot/${tnsrobot_id}/group/${group_id}/autoreporter`,
    DELETE_TNSROBOT_GROUP_AUTOREPORTER,
    { user_ids },
  );

export const addTNSRobotCoauthor = (tnsrobot_id, user_id) =>
  API.POST(
    `/api/tns_robot/${tnsrobot_id}/coauthor/${user_id}`,
    ADD_TNSROBOT_COAUTHOR,
  );

export const deleteTNSRobotCoauthor = (tnsrobot_id, user_id) =>
  API.DELETE(
    `/api/tns_robot/${tnsrobot_id}/coauthor/${user_id}`,
    DELETE_TNSROBOT_COAUTHOR,
  );

export const fetchTNSRobotSubmissions = (tnsrobot_id) =>
  API.GET(
    `/api/tns_robot/${tnsrobot_id}/submissions`,
    FETCH_TNSROBOT_SUBMISSIONS,
  );

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_TNSROBOTS) {
    if (payload?.group_id) {
      dispatch(fetchTNSRobots({ group_id: payload.group_id }));
    } else {
      dispatch(fetchTNSRobots());
    }
  }
});

const reducer = (state = { tnsrobotList: [], submissions: {} }, action) => {
  switch (action.type) {
    case FETCH_TNSROBOTS_OK: {
      const tnsrobotList = action.data;
      return {
        ...state,
        tnsrobotList,
      };
    }
    case FETCH_TNSROBOT_SUBMISSIONS_OK: {
      const { tnsrobot_id, submissions } = action.data;
      return {
        ...state,
        submissions: {
          ...state.submissions,
          [tnsrobot_id]: submissions,
        },
      };
    }
    default:
      return state;
  }
};

store.injectReducer("tnsrobots", reducer);
