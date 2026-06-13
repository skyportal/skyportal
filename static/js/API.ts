// Note: These are thunks (https://github.com/gaearon/redux-thunk),
// so calling `API(...)` will not do anything.
//
// Each invocation should happen inside of a `dispatch` call, e.g.,
//
//  dispatch(API.GET('/api/profile', FETCH_USER_PROFILE));
//

import { showNotification } from "baselayer/components/Notifications";

import type { AppDispatch } from "./types/store";

const API_CALL = "skyportal/API_CALL";

type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

/**
 * Shape of a successful API response (always wrapped in a {status,data,message}
 * envelope by `BaseHandler.success`).
 */
export interface ApiSuccess<T = unknown> {
  status: "success";
  message?: string;
  data: T;
}

/** Shape of a failed API response. */
export interface ApiError {
  status: "error";
  message: string;
}

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
 * The T parameter is the *data* shape returned by the endpoint (i.e. the
 * `data` field of {@link ApiSuccess}); pass it explicitly at the call site to
 * propagate the type into the dispatched _OK action and the reducer.
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
      /* In case of an unintentional error, dispatch an action that contains
           every piece of information we have about the request.

           This information can be used in a reducer to set an error message.
        */

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
): Record<string, unknown> => {
  const filteredParams: Record<string, unknown> = {};
  // Filter out empty fields from an object (form data)
  Object.keys(params).forEach((key) => {
    // Empty array ([]) counts as true, so specifically test for it
    // Also, the number 0 may be a valid input but evaluate to false,
    // so just let numbers through
    if (
      (!(
        Array.isArray(params[key]) &&
        (params[key] as unknown[]).length === 0 &&
        removeEmptyArrays
      ) &&
        (params[key] || (params[key] === false && removeFalse === false))) ||
      typeof key === "number"
    ) {
      filteredParams[key] = params[key];
    }
  });
  return filteredParams;
};

function GET<T = unknown>(
  endpoint: string,
  actionType?: string,
  queryParams?: Record<string, unknown>,
  removeFalse = true,
): ApiThunk<T> {
  let url = endpoint;
  if (queryParams) {
    const filteredQueryParams = filterOutEmptyValues(
      queryParams,
      true,
      removeFalse,
    );
    const queryString = new URLSearchParams(
      filteredQueryParams as Record<string, string>,
    ).toString();
    url += `?${queryString}`;
  }
  return API<T>(url, actionType, "GET");
}

function POST<T = unknown>(
  endpoint: string,
  actionType?: string,
  payload?: Record<string, unknown>,
): ApiThunk<T> {
  return API<T>(endpoint, actionType, "POST", payload);
}

function PATCH<T = unknown>(
  endpoint: string,
  actionType?: string,
  payload?: Record<string, unknown>,
): ApiThunk<T> {
  return API<T>(endpoint, actionType, "PATCH", payload);
}

function PUT<T = unknown>(
  endpoint: string,
  actionType?: string,
  payload?: Record<string, unknown>,
): ApiThunk<T> {
  return API<T>(endpoint, actionType, "PUT", payload);
}

function DELETE<T = unknown>(
  endpoint: string,
  actionType?: string,
  payload?: Record<string, unknown>,
): ApiThunk<T> {
  return API<T>(endpoint, actionType, "DELETE", payload);
}

function DOWNLOAD(
  endpoint: string,
  actionType?: string,
  payload: Record<string, any> = {},
): ApiThunk {
  // This is a special case where if the status is 200
  // there is no JSON to parse and return, instead the
  // browser will download the file directly.
  // if there is a failure, then we need to handle it like a normal API call
  return async (dispatch) => {
    if (!actionType) {
      dispatch(
        showNotification(
          "API invocation error: no actionType specified",
          "error",
        ),
      );
    }
    const filename = payload?.["filename"] || "download";
    delete payload["filename"];

    dispatch({
      type: actionType ?? API_CALL,
      parameters: { endpoint, payload },
    });
    try {
      const response = await fetch(endpoint, {
        method: "GET",
        credentials: "same-origin",
      });

      if (response.status === 200) {
        return response.blob().then((blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
        });
      }

      const json = await response.json();
      dispatch(showNotification(`${json.message}`, "error"));
      return dispatch({ type: `${actionType}_ERROR`, ...json });
    } catch (error: any) {
      dispatch(showNotification(`${error.message}`, "error"));
      return dispatch({
        type: `${actionType}_FAIL`,
        parameters: { endpoint, payload },
        status: "error",
        message: error.message,
      });
    }
  };
}

export { GET, POST, PUT, PATCH, DELETE, API, DOWNLOAD, API_CALL };
