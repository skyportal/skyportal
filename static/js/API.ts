// These are thunks (https://github.com/gaearon/redux-thunk): calling `API(...)`
// does nothing until it is dispatched, e.g. dispatch(GET('/api/profile', TYPE)).

import { showNotification } from "baselayer/components/Notifications";

import type { AppDispatch } from "./types/store";

const API_CALL = "skyportal/API_CALL";

type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

/** Action dispatched after a successful API call: type=<actionType>_OK. */
export type ApiOkAction<T = unknown> = {
  type: string;
  status: "success";
  message?: string;
  data: T;
  parameters: ApiCallParameters;
};

interface ApiCallParameters {
  endpoint: string;
  actionType?: string;
  body: Record<string, unknown>;
  method: HttpMethod;
  otherArgs: Record<string, unknown>;
}

/**
 * A redux-thunk returned by the API helpers; dispatch it to run the request.
 * T is the *data* field of the response envelope; pass it explicitly at the
 * call site to propagate the type into the _OK action and the reducer.
 */
export type ApiThunk<T = unknown> = (
  dispatch: AppDispatch,
) => Promise<ApiOkAction<T> | { type: string; [k: string]: unknown }>;

function API<T = unknown>(
  endpoint: string,
  actionType?: string,
  method: HttpMethod = "GET",
  body: Record<string, unknown> = {},
  otherArgs: Record<string, unknown> = {},
): ApiThunk<T> {
  const parameters = { endpoint, actionType, body, method, otherArgs };

  let fetchInit: RequestInit = {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
    },
    method,
    ...otherArgs,
  };
  if (method !== "GET") {
    fetchInit = { ...fetchInit, body: JSON.stringify(body) };
  }

  return async (dispatch) => {
    if (!actionType) {
      dispatch(
        showNotification(
          "API invocation error: no actionType specified",
          "error",
        ),
      );
    }
    dispatch({ type: actionType ?? API_CALL, parameters });
    try {
      const response = await fetch(endpoint, fetchInit);

      let json: any = "";
      try {
        json = await response.json();
      } catch (error: any) {
        throw new Error(`JSON decoding error: ${error}`);
      }

      if (json.status !== "success") {
        dispatch(showNotification(`${json.message}`, "error"));
        return dispatch({ type: `${actionType}_ERROR`, ...json });
      }

      return dispatch({ type: `${actionType}_OK`, ...json, parameters });
    } catch (error: any) {
      dispatch(showNotification(`${error.message}`, "error"));
      return dispatch({
        type: `${actionType}_FAIL`,
        parameters,
        status: "error",
        message: error.message,
      });
    }
  };
}

export const filterOutEmptyValues = (
  params: Record<string, unknown>,
  removeEmptyArrays = true,
  removeFalse = true,
): Record<string, unknown> =>
  Object.fromEntries(
    Object.entries(params).filter(([, value]) => {
      // 0 is falsy but a valid input (this tested the key, never a number, until #6416)
      if (Number.isFinite(value)) return true;
      if (removeEmptyArrays && Array.isArray(value) && value.length === 0)
        return false;
      return Boolean(value) || (value === false && !removeFalse);
    }),
  );

export const pickParams = (
  params: Record<string, any>,
  keys: readonly string[],
): Record<string, any> =>
  Object.fromEntries(
    Object.entries(params).filter(([key]) => keys.includes(key)),
  );

/**
 * Encode an object as a URL query string (no leading "?"), skipping null,
 * undefined, "" and empty arrays. Use this everywhere query params are built so
 * the encoding/skipping rules stay consistent across ducks.
 */
export const buildQueryString = (params: Record<string, unknown>): string => {
  const search = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (
      value === null ||
      value === undefined ||
      value === "" ||
      (Array.isArray(value) && value.length === 0)
    ) {
      return;
    }
    search.append(key, String(value));
  });
  return search.toString();
};

function GET<T = unknown>(
  endpoint: string,
  actionType?: string,
  queryParams?: Record<string, unknown>,
  removeFalse = true,
): ApiThunk<T> {
  const url = queryParams
    ? `${endpoint}?${buildQueryString(
        filterOutEmptyValues(queryParams, true, removeFalse),
      )}`
    : endpoint;
  return API<T>(url, actionType, "GET");
}

function POST<T = unknown>(
  endpoint: string,
  actionType?: string,
  payload?: Record<string, unknown>,
): ApiThunk<T> {
  return API<T>(endpoint, actionType, "POST", payload);
}

function DOWNLOAD(
  endpoint: string,
  actionType?: string,
  payload: Record<string, any> = {},
): ApiThunk {
  // On success the browser downloads the file directly, so there is no JSON to
  // parse; only a failure is handled like a normal API call.
  const { filename, ...parameters } = payload;

  return async (dispatch) => {
    if (!actionType) {
      dispatch(
        showNotification(
          "API invocation error: no actionType specified",
          "error",
        ),
      );
    }

    dispatch({
      type: actionType ?? API_CALL,
      parameters: { endpoint, payload: parameters },
    });
    try {
      const response = await fetch(endpoint, {
        method: "GET",
        credentials: "same-origin",
      });

      if (response.status === 200) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename || "download";
        document.body.appendChild(a);
        a.click();
        a.remove();
        return;
      }

      const json = await response.json();
      dispatch(showNotification(`${json.message}`, "error"));
      return dispatch({ type: `${actionType}_ERROR`, ...json });
    } catch (error: any) {
      dispatch(showNotification(`${error.message}`, "error"));
      return dispatch({
        type: `${actionType}_FAIL`,
        parameters: { endpoint, payload: parameters },
        status: "error",
        message: error.message,
      });
    }
  };
}

export { GET, POST, API, DOWNLOAD, API_CALL };
