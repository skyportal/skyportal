import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_GROUP_ADMISSION_REQUESTS =
  "skyportal/FETCH_GROUP_ADMISSION_REQUESTS";
const FETCH_GROUP_ADMISSION_REQUESTS_OK =
  "skyportal/FETCH_GROUP_ADMISSION_REQUESTS_OK";

const DELETE_GROUP_ADMISSION_REQUEST =
  "skyportal/DELETE_GROUP_ADMISSION_REQUEST";

const REQUEST_GROUP_ADMISSION = "skyportal/REQUEST_GROUP_ADMISSION";

const UPDATE_ADMISSION_REQUEST_STATUS =
  "skyportal/UPDATE_ADMISSION_REQUEST_STATUS";

export function fetchGroupAdmissionRequests(groupID) {
  return API.GET(
    `/api/group_admission_requests?groupID=${groupID}`,
    FETCH_GROUP_ADMISSION_REQUESTS,
  );
}

export const requestGroupAdmission = (userID, groupID) =>
  API.POST("/api/group_admission_requests", REQUEST_GROUP_ADMISSION, {
    userID,
    groupID,
  });

export const deleteAdmissionRequest = (ID) =>
  API.DELETE(
    `/api/group_admission_requests/${ID}`,
    DELETE_GROUP_ADMISSION_REQUEST,
  );

export const updateAdmissionRequestStatus = ({ requestID, status }) =>
  API.PATCH(
    `/api/group_admission_requests/${requestID}`,
    UPDATE_ADMISSION_REQUEST_STATUS,
    { status },
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_GROUP_ADMISSION_REQUESTS) {
    dispatch(fetchGroupAdmissionRequests(payload.group_id));
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_GROUP_ADMISSION_REQUESTS_OK: {
      const { data } = action;
      // action.data is an array of records
      const groupID = data[0]?.group_id;
      return { [groupID]: action.data };
    }
    default:
      return state;
  }
};

store.injectReducer("groupAdmissionRequests", reducer);
