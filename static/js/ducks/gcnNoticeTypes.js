import * as API from "../API";
import store from "../store";

const FETCH_GCN_NOTICE_TYPES = "skyportal/FETCH_GCN_NOTICE_TYPES";
const FETCH_GCN_NOTICE_TYPES_OK = "skyportal/FETCH_GCN_NOTICE_TYPES_OK";

// eslint-disable-next-line import/prefer-default-export
export const fetchGcnNoticeTypes = () =>
  API.GET("/api/gcn_notice_types", FETCH_GCN_NOTICE_TYPES);

const reducer = (state = { gcnNoticeTypes: [] }, action) => {
  switch (action.type) {
    case FETCH_GCN_NOTICE_TYPES_OK: {
      const gcnNoticeTypes = action.data;
      return {
        ...state,
        gcnNoticeTypes,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("gcnNoticeTypes", reducer);
