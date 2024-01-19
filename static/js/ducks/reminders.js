import messageHandler from "baselayer/MessageHandler";
import * as API from "../API";
import store from "../store";

const FETCH_REMINDERS = "skyportal/FETCH_REMINDERS";
const FETCH_REMINDERS_OK = "skyportal/FETCH_REMINDERS_OK";

const SUBMIT_REMINDER = "skyportal/SUBMIT_REMINDER";

const DELETE_REMINDER = "skyportal/DELETE_REMINDER";

const UPDATE_REMINDER = "skyportal/UPDATE_REMINDER";

export function fetchReminders(resourceId, resourceType) {
  return API.GET(
    `/api/${resourceType}/${resourceId}/reminders`,
    FETCH_REMINDERS,
  );
}

export function submitReminder(resourceId, resourceType, data) {
  return API.POST(
    `/api/${resourceType}/${resourceId}/reminders`,
    SUBMIT_REMINDER,
    data,
  );
}

export function updateReminder(resourceId, resourceType, reminderID, data) {
  return API.PATCH(
    `/api/${resourceType}/${resourceId}/reminders/${reminderID}`,
    UPDATE_REMINDER,
    data,
  );
}

export function deleteReminder(resourceId, resourceType, reminderID) {
  return API.DELETE(
    `/api/${resourceType}/${resourceId}/reminders/${reminderID}`,
    DELETE_REMINDER,
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { reminders } = getState();
  switch (actionType) {
    case "skyportal/REFRESH_REMINDER_SOURCE": {
      if (
        reminders.resourceId === payload.id &&
        reminders.resourceType === "source"
      ) {
        dispatch(fetchReminders(reminders.resourceId, reminders.resourceType));
      }
      break;
    }
    case "skyportal/REFRESH_REMINDER_GCNEVENT": {
      if (
        reminders.resourceId === payload.id &&
        reminders.resourceType === "gcn_event"
      ) {
        dispatch(fetchReminders(reminders.resourceId, reminders.resourceType));
      }
      break;
    }
    case "skyportal/REFRESH_REMINDER_SOURCE_SPECTRA": {
      if (
        reminders.resourceId === payload.id &&
        reminders.resourceType === "spectra"
      ) {
        dispatch(fetchReminders(reminders.resourceId, reminders.resourceType));
      }
      break;
    }
    case "skyportal/REFRESH_REMINDER_SHIFT": {
      if (
        reminders.resourceId === payload.id &&
        reminders.resourceType === "shift"
      ) {
        dispatch(fetchReminders(reminders.resourceId, reminders.resourceType));
      }
      break;
    }
    default: {
      // do nothing
      break;
    }
  }
});

const reducer = (
  state = { resourceId: null, resourceType: null, remindersList: [] },
  action,
) => {
  switch (action.type) {
    case FETCH_REMINDERS_OK: {
      const { resourceId, resourceType, reminders } = action.data;
      return {
        resourceId,
        resourceType,
        remindersList: reminders,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("reminders", reducer);
