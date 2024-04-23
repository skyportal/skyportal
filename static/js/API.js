// Note: These are thunks (https://github.com/gaearon/redux-thunk),
// so calling `API(...)` will not do anything.
//
// Each invocation should happen inside of a `dispatch` call, e.g.,
//
//  dispatch(API.GET('/api/profile', FETCH_USER_PROFILE));
//

import { showNotification } from "baselayer/components/Notifications";

const API_CALL = "skyportal/API_CALL";

function API(endpoint, actionType, method = "GET", body = {}, otherArgs = {}) {
  const parameters = { endpoint, actionType, body, method, otherArgs };

  let fetchInit = {
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
    dispatch({ type: actionType, parameters });
    try {
      const response = await fetch(endpoint, fetchInit);

      let json = "";
      try {
        json = await response.json();
      } catch (error) {
        throw new Error(`JSON decoding error: ${error}`);
      }

      if (json.status !== "success") {
        dispatch(showNotification(`${json.message}`, "error"));
        return dispatch({ type: `${actionType}_ERROR`, ...json });
      }

      return dispatch({ type: `${actionType}_OK`, ...json });
    } catch (error) {
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

export const filterOutEmptyValues = (params, removeEmptyArrays = true) => {
  const filteredParams = {};
  // Filter out empty fields from an object (form data)
  Object.keys(params).forEach((key) => {
    // Empty array ([]) counts as true, so specifically test for it
    // Also, the number 0 may be a valid input but evaluate to false,
    // so just let numbers through
    if (
      !(
        Array.isArray(params[key]) &&
        params[key].length === 0 &&
        removeEmptyArrays
      ) ||
      typeof key === "number"
    ) {
      filteredParams[key] = params[key];
    }
  });
  return filteredParams;
};

function GET(endpoint, actionType, queryParams) {
  let url = endpoint;
  if (queryParams) {
    const filteredQueryParams = filterOutEmptyValues(queryParams);
    const queryString = new URLSearchParams(filteredQueryParams).toString();
    url += `?${queryString}`;
  }
  return API(url, actionType, "GET");
}

function POST(endpoint, actionType, payload) {
  return API(endpoint, actionType, "POST", payload);
}

function PATCH(endpoint, actionType, payload) {
  return API(endpoint, actionType, "PATCH", payload);
}

function PUT(endpoint, actionType, payload) {
  return API(endpoint, actionType, "PUT", payload);
}

function DELETE(endpoint, actionType, payload) {
  return API(endpoint, actionType, "DELETE", payload);
}

export { GET, POST, PUT, PATCH, DELETE, API, API_CALL };
