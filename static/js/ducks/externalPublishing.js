import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_EXTERNAL_PUBLISHING_BOTS =
  "skyportal/FETCH_EXTERNAL_PUBLISHING_BOTS";
const FETCH_EXTERNAL_PUBLISHING_BOTS_OK =
  "skyportal/FETCH_EXTERNAL_PUBLISHING_BOTS_OK";

const ADD_EXTERNAL_PUBLISHING_BOT = "skyportal/ADD_EXTERNAL_PUBLISHING_BOT";
const EDIT_EXTERNAL_PUBLISHING_BOT = "skyportal/EDIT_EXTERNAL_PUBLISHING_BOT";
const DELETE_EXTERNAL_PUBLISHING_BOT =
  "skyportal/DELETE_EXTERNAL_PUBLISHING_BOT";
const REFRESH_EXTERNAL_PUBLISHING_BOTS =
  "skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS";

const ADD_EXTERNAL_PUBLISHING_BOT_GROUP =
  "skyportal/ADD_EXTERNAL_PUBLISHING_BOT_GROUP";
const EDIT_EXTERNAL_PUBLISHING_BOT_GROUP =
  "skyportal/EDIT_EXTERNAL_PUBLISHING_BOT_GROUP";
const DELETE_EXTERNAL_PUBLISHING_BOT_GROUP =
  "skyportal/DELETE_EXTERNAL_PUBLISHING_BOT_GROUP";

const ADD_EXTERNAL_PUBLISHING_BOT_GROUP_AUTOREPORTER =
  "skyportal/ADD_EXTERNAL_PUBLISHING_BOT_GROUP_AUTOREPORTER";
const DELETE_EXTERNAL_PUBLISHING_BOT_GROUP_AUTOREPORTER =
  "skyportal/DELETE_EXTERNAL_PUBLISHING_BOT_GROUP_AUTOREPORTER";

const ADD_EXTERNAL_PUBLISHING_BOT_COAUTHOR =
  "skyportal/ADD_EXTERNAL_PUBLISHING_BOT_COAUTHOR";
const DELETE_EXTERNAL_PUBLISHING_BOT_COAUTHOR =
  "skyportal/DELETE_EXTERNAL_PUBLISHING_BOT_COAUTHOR";

const FETCH_EXTERNAL_PUBLISHING_SUBMISSIONS =
  "skyportal/FETCH_EXTERNAL_PUBLISHING_SUBMISSIONS";
const FETCH_EXTERNAL_PUBLISHING_SUBMISSIONS_OK =
  "skyportal/FETCH_EXTERNAL_PUBLISHING_SUBMISSIONS_OK";

export const fetchExternalPublishingBots = (params = {}) =>
  API.GET(
    "/api/external_publishing_bot",
    FETCH_EXTERNAL_PUBLISHING_BOTS,
    params,
  );

export const addExternalPublishingBot = (data) =>
  API.PUT("/api/external_publishing_bot", ADD_EXTERNAL_PUBLISHING_BOT, data);

export const editExternalPublishingBot = (id, data) =>
  API.PUT(
    `/api/external_publishing_bot/${id}`,
    EDIT_EXTERNAL_PUBLISHING_BOT,
    data,
  );

export const deleteExternalPublishingBot = (id) =>
  API.DELETE(
    `/api/external_publishing_bot/${id}`,
    DELETE_EXTERNAL_PUBLISHING_BOT,
  );

export const addExternalPublishingBotGroup = (
  external_publishing_bot_id,
  data,
) =>
  API.PUT(
    `/api/external_publishing_bot/${external_publishing_bot_id}/group`,
    ADD_EXTERNAL_PUBLISHING_BOT_GROUP,
    data,
  );

export const editExternalPublishingBotGroup = (
  external_publishing_bot_id,
  group_id,
  data,
) =>
  API.PUT(
    `/api/external_publishing_bot/${external_publishing_bot_id}/group/${group_id}`,
    EDIT_EXTERNAL_PUBLISHING_BOT_GROUP,
    data,
  );

export const deleteExternalPublishingBotGroup = (
  external_publishing_bot_id,
  group_id,
) =>
  API.DELETE(
    `/api/external_publishing_bot/${external_publishing_bot_id}/group/${group_id}`,
    DELETE_EXTERNAL_PUBLISHING_BOT_GROUP,
  );

export const addExternalPublishingBotGroupAutoReporters = (
  external_publishing_bot_id,
  group_id,
  user_ids = [],
) =>
  API.POST(
    `/api/external_publishing_bot/${external_publishing_bot_id}/group/${group_id}/autoreporter`,
    ADD_EXTERNAL_PUBLISHING_BOT_GROUP_AUTOREPORTER,
    { user_ids },
  );

export const deleteExternalPublishingBotGroupAutoReporters = (
  external_publishing_bot_id,
  group_id,
  user_ids = [],
) =>
  API.DELETE(
    `/api/external_publishing_bot/${external_publishing_bot_id}/group/${group_id}/autoreporter`,
    DELETE_EXTERNAL_PUBLISHING_BOT_GROUP_AUTOREPORTER,
    { user_ids },
  );

export const addExternalPublishingBotCoauthor = (
  external_publishing_bot_id,
  user_id,
) =>
  API.POST(
    `/api/external_publishing_bot/${external_publishing_bot_id}/coauthor/${user_id}`,
    ADD_EXTERNAL_PUBLISHING_BOT_COAUTHOR,
  );

export const deleteExternalPublishingBotCoauthor = (
  external_publishing_bot_id,
  user_id,
) =>
  API.DELETE(
    `/api/external_publishing_bot/${external_publishing_bot_id}/coauthor/${user_id}`,
    DELETE_EXTERNAL_PUBLISHING_BOT_COAUTHOR,
  );

export const fetchExternalPublishingSubmissions = (
  external_publishing_bot_id,
  params,
) =>
  API.GET(
    `/api/external_publishing/${external_publishing_bot_id}/submissions`,
    FETCH_EXTERNAL_PUBLISHING_SUBMISSIONS,
    {
      ...params,
      include_payload: true,
    },
  );

messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_EXTERNAL_PUBLISHING_BOTS) {
    if (payload?.group_id) {
      dispatch(fetchExternalPublishingBots({ group_id: payload.group_id }));
    } else {
      dispatch(fetchExternalPublishingBots());
    }
  }
});

const reducer = (
  state = { externalPublishingBotList: null, submissions: {} },
  action,
) => {
  switch (action.type) {
    case FETCH_EXTERNAL_PUBLISHING_BOTS_OK: {
      const externalPublishingBotList = action.data;
      return {
        ...state,
        externalPublishingBotList,
      };
    }
    case FETCH_EXTERNAL_PUBLISHING_SUBMISSIONS_OK: {
      const { external_publishing_bot_id, submissions, totalMatches } =
        action.data;
      return {
        ...state,
        submissions: {
          ...state.submissions,
          [external_publishing_bot_id]: {
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

store.injectReducer("externalPublishingBots", reducer);
