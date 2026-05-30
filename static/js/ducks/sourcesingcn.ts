import * as API from "../API";
import store from "../store";

const FETCH_SOURCES_IN_GCN = "skyportal/FETCH_SOURCES_IN_GCN";
const FETCH_SOURCES_IN_GCN_OK = "skyportal/FETCH_SOURCES_IN_GCN_OK";

const SUBMIT_SOURCE_IN_GCN = "skyportal/SUBMIT_SOURCE_IN_GCN";

const DELETE_SOURCE_IN_GCN = "skyportal/DELETE_SOURCE_IN_GCN";

const PATCH_SOURCE_IN_GCN = "skyportal/PATCH_SOURCE_IN_GCN";

export const fetchSourcesInGcn = (dateobs: string, data: any) =>
  API.GET(`/api/sources_in_gcn/${dateobs}`, FETCH_SOURCES_IN_GCN, data);

export const submitSourceInGcn = (dateobs: string, data: any) =>
  API.POST(`/api/sources_in_gcn/${dateobs}`, SUBMIT_SOURCE_IN_GCN, data);

export const deleteSourceInGcn = (
  dateobs: string,
  source_id: number | string,
) =>
  API.DELETE(
    `/api/sources_in_gcn/${dateobs}/${source_id}`,
    DELETE_SOURCE_IN_GCN,
  );

export const patchSourceInGcn = (
  dateobs: string,
  source_id: number | string,
  data: any,
) =>
  API.PATCH(
    `/api/sources_in_gcn/${dateobs}/${source_id}`,
    PATCH_SOURCE_IN_GCN,
    data,
  );

interface SourcesInGcnAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: Record<string, any> = { sourcesingcn: [] },
  action: SourcesInGcnAction,
) => {
  switch (action.type) {
    case FETCH_SOURCES_IN_GCN_OK: {
      const sourcesingcn = action.data;
      return {
        ...state,
        sourcesingcn,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("sourcesingcn", reducer);
