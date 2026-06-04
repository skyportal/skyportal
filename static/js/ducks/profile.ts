import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_USER_PROFILE = "skyportal/FETCH_USER_PROFILE";
const FETCH_USER_PROFILE_OK = "skyportal/FETCH_USER_PROFILE_OK";

const GENERATE_TOKEN = "skyportal/GENERATE_TOKEN";

const UPDATE_TOKEN = "skyportal/UPDATE_TOKEN";

const UPDATE_USER_PREFERENCES = "skyportal/UPDATE_USER_PREFERENCES";

const UPDATE_BASIC_USER_INFO = "skyportal/UPDATE_BASIC_USER_INFO";

const DELETE_TOKEN = "skyportal/DELETE_TOKEN";

export function updateUserPreferences(preferences: any) {
  return API.PATCH("/api/internal/profile", UPDATE_USER_PREFERENCES, {
    preferences,
  });
}

export function updateBasicUserInfo(formData: any, user_id?: number | string) {
  return API.PATCH(
    `/api/internal/profile${user_id ? `/${user_id}` : ""}`,
    UPDATE_BASIC_USER_INFO,
    formData,
  );
}

export function fetchUserProfile() {
  return API.GET("/api/internal/profile", FETCH_USER_PROFILE);
}

export function createToken(form_data: any) {
  return API.POST("/api/internal/tokens", GENERATE_TOKEN, form_data);
}

export function updateToken(tokenID: number | string, form_data: any) {
  return API.PUT(`/api/internal/tokens/${tokenID}`, UPDATE_TOKEN, form_data);
}

export function deleteToken(tokenID: number | string) {
  return API.DELETE(`/api/internal/tokens/${tokenID}`, DELETE_TOKEN);
}

// Websocket message handler
messageHandler.add((actionType: any, _payload: any, dispatch: any) => {
  if (actionType === FETCH_USER_PROFILE) {
    dispatch(fetchUserProfile());
  }
});

const initialState: Record<string, any> = {
  username: "",
  first_name: null,
  id: null,
  last_name: null,
  contact_email: null,
  contact_phone: null,
  gravatar_url: "",
  roles: [],
  acls: [],
  permissions: [],
  tokens: [],
  preferences: {},
  groupAdmissionRequests: [],
};

interface ProfileAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: Record<string, any> = initialState,
  action: ProfileAction,
): Record<string, any> => {
  switch (action.type) {
    case FETCH_USER_PROFILE_OK:
      return action.data;
    default:
      return state;
  }
};

store.injectReducer("profile", reducer);
