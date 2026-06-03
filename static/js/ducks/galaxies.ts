import messageHandler from "baselayer/MessageHandler";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import * as API from "../API";
import store from "../store";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const FETCH_GALAXIES = "skyportal/FETCH_GALAXIES";
const FETCH_GALAXIES_OK = "skyportal/FETCH_GALAXIES_OK";

const FETCH_GCNEVENT_GALAXIES = "skyportal/FETCH_GCNEVENT_GALAXIES";
const FETCH_GCNEVENT_GALAXIES_OK = "skyportal/FETCH_GCNEVENT_GALAXIES_OK";

const DELETE_GALAXIES = "skyportal/DELETE_GALAXIES";

const UPLOAD_GALAXIES = "skyportal/UPLOAD_GALAXIES";

const FETCH_GALAXY_CATALOGS = "skyportal/FETCH_GALAXY_CATALOGS";
const FETCH_GALAXY_CATALOGS_OK = "skyportal/FETCH_GALAXY_CATALOGS_OK";

export function uploadGalaxies(data: any) {
  return API.POST(`/api/galaxy_catalog/ascii`, UPLOAD_GALAXIES, data);
}

export function fetchGalaxies(filterParams: Record<string, any> = {}) {
  return API.GET("/api/galaxy_catalog", FETCH_GALAXIES, filterParams);
}

export function deleteCatalog(catalog: string) {
  return API.DELETE(`/api/galaxy_catalog/${catalog}`, DELETE_GALAXIES);
}

export function fetchCatalogs(filterParams: Record<string, any> = {}) {
  filterParams["catalogNamesOnly"] = true;
  return API.GET("/api/galaxy_catalog", FETCH_GALAXIES, filterParams);
}

export function fetchGcnEventGalaxies(
  dateobs: string,
  filterParams: Record<string, any> = {},
) {
  filterParams["localizationDateobs"] = dateobs;
  filterParams["includeGeoJSON"] = true;

  return API.GET("/api/galaxy_catalog", FETCH_GCNEVENT_GALAXIES, filterParams);
}

export const fetchGalaxyCatalogs = () =>
  API.GET("/api/galaxy_catalog?catalogNamesOnly=true", FETCH_GALAXY_CATALOGS);

// Websocket message handler
messageHandler.add(
  (actionType: string, payload: any, dispatch: any, getState: any) => {
    const { gcnEvent } = getState();
    if (actionType === FETCH_GCNEVENT_GALAXIES) {
      if (gcnEvent && gcnEvent.id === payload.gcnEvent.id) {
        dispatch(fetchGcnEventGalaxies(gcnEvent.dateobs));
      }
    }
  },
);

interface GalaxiesAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (state: any = null, action: GalaxiesAction) => {
  switch (action.type) {
    case FETCH_GALAXIES_OK: {
      return {
        ...state,
        galaxies: action.data,
      };
    }
    case FETCH_GCNEVENT_GALAXIES_OK: {
      return {
        ...state,
        gcnEventGalaxies: action.data,
      };
    }
    case FETCH_GALAXY_CATALOGS_OK: {
      return {
        ...state,
        catalogs: action.data,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("galaxies", reducer);
