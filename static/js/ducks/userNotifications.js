import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_NOTIFICATIONS = "skyportal/FETCH_NOTIFICATIONS";
const FETCH_NOTIFICATIONS_OK = "skyportal/FETCH_NOTIFICATIONS_OK";

const UPDATE_NOTIFICATION = "skyportal/UPDATE_NOTIFICATION";
const UPDATE_ALL_NOTIFICATIONS = "skyportal/UPDATE_ALL_NOTIFICATIONS";

const DELETE_NOTIFICATION = "skyportal/DELETE_NOTIFICATION";
const DELETE_ALL_NOTIFICATIONS = "skyportal/DELETE_ALL_NOTIFICATIONS";

const TEST_NOTIFICATIONS = "skyportal/TEST_NOTIFICATIONS";

export const testNotifications = (data) =>
  API.POST("/api/internal/notifications_test", TEST_NOTIFICATIONS, data);

export const fetchNotifications = () =>
  API.GET("/api/internal/notifications", FETCH_NOTIFICATIONS);

export const updateNotification = ({ notificationID, data }) =>
  API.PATCH(
    `/api/internal/notifications/${notificationID}`,
    UPDATE_NOTIFICATION,
    data
  );

export const updateAllNotifications = (data) =>
  API.PATCH("/api/internal/notifications/all", UPDATE_ALL_NOTIFICATIONS, data);

export const deleteAllNotifications = () =>
  API.DELETE("/api/internal/notifications/all", DELETE_ALL_NOTIFICATIONS);

export const deleteNotification = (notificationID) =>
  API.DELETE(
    `/api/internal/notifications/${notificationID}`,
    DELETE_NOTIFICATION
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_NOTIFICATIONS) {
    dispatch(fetchNotifications());
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_NOTIFICATIONS_OK:
      return action.data;
    default:
      return state;
  }
};

store.injectReducer("userNotifications", reducer);
