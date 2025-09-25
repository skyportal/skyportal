import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_SHARING_SERVICES = "skyportal/FETCH_SHARING_SERVICES";
const FETCH_SHARING_SERVICES_OK = "skyportal/FETCH_SHARING_SERVICES_OK";

const ADD_SHARING_SERVICE = "skyportal/ADD_SHARING_SERVICE";
const EDIT_SHARING_SERVICE = "skyportal/EDIT_SHARING_SERVICE";
const DELETE_SHARING_SERVICE = "skyportal/DELETE_SHARING_SERVICE";
const REFRESH_SHARING_SERVICES = "skyportal/REFRESH_SHARING_SERVICES";

const ADD_SHARING_SERVICE_GROUP = "skyportal/ADD_SHARING_SERVICE_GROUP";
const EDIT_SHARING_SERVICE_GROUP = "skyportal/EDIT_SHARING_SERVICE_GROUP";
const DELETE_SHARING_SERVICE_GROUP = "skyportal/DELETE_SHARING_SERVICE_GROUP";

const ADD_SHARING_SERVICE_GROUP_AUTO_PUBLISHER =
  "skyportal/ADD_SHARING_SERVICE_GROUP_AUTO_PUBLISHER";
const DELETE_SHARING_SERVICE_GROUP_AUTO_PUBLISHERS =
  "skyportal/DELETE_SHARING_SERVICE_GROUP_AUTO_PUBLISHERS";

const ADD_SHARING_SERVICE_COAUTHOR = "skyportal/ADD_SHARING_SERVICE_COAUTHOR";
const DELETE_SHARING_SERVICE_COAUTHOR =
  "skyportal/DELETE_SHARING_SERVICE_COAUTHOR";

const ADD_SHARING_SERVICE_SUBMISSION =
  "skyportal/ADD_SHARING_SERVICE_SUBMISSION";
const FETCH_SHARING_SERVICE_SUBMISSIONS =
  "skyportal/FETCH_SHARING_SERVICE_SUBMISSIONS";
const FETCH_SHARING_SERVICE_SUBMISSIONS_OK =
  "skyportal/FETCH_SHARING_SERVICE_SUBMISSIONS_OK";
const REFRESH_SHARING_SERVICE_SUBMISSIONS =
  "skyportal/REFRESH_SHARING_SERVICE_SUBMISSIONS";

export const fetchSharingServices = (params = {}) =>
  API.GET("/api/sharing_service", FETCH_SHARING_SERVICES, params);

export const addSharingService = (data) =>
  API.PUT("/api/sharing_service", ADD_SHARING_SERVICE, data);

export const editSharingService = (id, data) =>
  API.PUT(`/api/sharing_service/${id}`, EDIT_SHARING_SERVICE, data);

export const deleteSharingService = (id) =>
  API.DELETE(`/api/sharing_service/${id}`, DELETE_SHARING_SERVICE);

export const addSharingServiceGroup = (sharing_service_id, data) =>
  API.PUT(
    `/api/sharing_service/${sharing_service_id}/group`,
    ADD_SHARING_SERVICE_GROUP,
    data,
  );

export const editSharingServiceGroup = (sharing_service_id, group_id, data) =>
  API.PUT(
    `/api/sharing_service/${sharing_service_id}/group/${group_id}`,
    EDIT_SHARING_SERVICE_GROUP,
    data,
  );

export const deleteSharingServiceGroup = (sharing_service_id, group_id) =>
  API.DELETE(
    `/api/sharing_service/${sharing_service_id}/group/${group_id}`,
    DELETE_SHARING_SERVICE_GROUP,
  );

export const addSharingServiceGroupAutoPublishers = (
  sharing_service_id,
  group_id,
  user_ids = [],
) =>
  API.POST(
    `/api/sharing_service/${sharing_service_id}/group/${group_id}/auto_publisher`,
    ADD_SHARING_SERVICE_GROUP_AUTO_PUBLISHER,
    { user_ids },
  );

export const deleteSharingServiceGroupAutoPublishers = (
  sharing_service_id,
  group_id,
  user_ids = [],
) =>
  API.DELETE(
    `/api/sharing_service/${sharing_service_id}/group/${group_id}/auto_publisher`,
    DELETE_SHARING_SERVICE_GROUP_AUTO_PUBLISHERS,
    { user_ids },
  );

export const addSharingServiceCoauthor = (sharing_service_id, user_id) =>
  API.POST(
    `/api/sharing_service/${sharing_service_id}/coauthor/${user_id}`,
    ADD_SHARING_SERVICE_COAUTHOR,
  );

export const deleteSharingServiceCoauthor = (sharing_service_id, user_id) =>
  API.DELETE(
    `/api/sharing_service/${sharing_service_id}/coauthor/${user_id}`,
    DELETE_SHARING_SERVICE_COAUTHOR,
  );

export function addSharingServiceSubmission(formData) {
  return API.POST(
    `/api/sharing_service/submission`,
    ADD_SHARING_SERVICE_SUBMISSION,
    formData,
  );
}

export const fetchSharingServiceSubmissions = (params = {}) =>
  API.GET(
    `/api/sharing_service/submission`,
    FETCH_SHARING_SERVICE_SUBMISSIONS,
    {
      ...params,
      include_payload: true,
    },
  );

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_SHARING_SERVICES) {
    if (payload?.group_id) {
      dispatch(fetchSharingServices({ group_id: payload.group_id }));
    } else {
      dispatch(fetchSharingServices());
    }
  } else if (actionType === REFRESH_SHARING_SERVICE_SUBMISSIONS) {
    dispatch(
      fetchSharingServiceSubmissions({
        sharing_service_id: payload.sharing_service_id,
      }),
    );
  }
});

const reducer = (
  state = { sharingServicesList: [], submissions: {}, loading: false },
  action,
) => {
  switch (action.type) {
    case FETCH_SHARING_SERVICES: {
      return { ...state, loading: true };
    }
    case FETCH_SHARING_SERVICES_OK: {
      const sharingServicesList = action.data;
      return {
        ...state,
        sharingServicesList,
        loading: false,
      };
    }
    case FETCH_SHARING_SERVICE_SUBMISSIONS_OK: {
      const { sharing_service_id, submissions, totalMatches } = action.data;
      return {
        ...state,
        submissions: {
          ...state.submissions,
          [sharing_service_id]: {
            totalMatches,
            submissions,
          },
        },
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sharingServices", reducer);
