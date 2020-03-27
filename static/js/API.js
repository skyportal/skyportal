// Note: These are thunks (https://github.com/gaearon/redux-thunk),
// so calling `API(...)` will not do anything.
//
// Each invocation should happen inside of a `dispatch` call, e.g.,
//
//  dispatch(API.GET('/api/profile', FETCH_USER_PROFILE));
//

import { showNotification } from 'baselayer/components/Notifications';

const API_CALL = 'skyportal/API_CALL';

function API(endpoint, actionType, method='GET', body={}, otherArgs={}) {
  const parameters = { endpoint, actionType, body, method, otherArgs };

  let fetchInit = {
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json'
    },
    method,
    ...otherArgs
  };
  if (method !== 'GET') {
    fetchInit = { ...fetchInit, body: JSON.stringify(body) };
  }

  return (
    async (dispatch) => {
      if (!actionType) {
        return dispatch(
          showNotification(
            'API invocation error: no actionType specified',
            'error'
          )
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
          throw new Error(`Backend error: ${json.message}`);
        }
        return dispatch({ type: `${actionType}_OK`, ...json });
      } catch (error) {
        /* In case of an error, dispatch an action that contains
           every piece of information we have about the request, including
           JSON args, and the response that came back from the server.

           This information can be used in a reducer to set an error message.
        */

        dispatch({ type: `${actionType}_FAIL`, parameters, error: error.message });
        return dispatch(showNotification(`${error.message}`, 'error'));
      }
    }
  );
}

function GET(endpoint, actionType) {
  return API(endpoint, actionType, 'GET');
}

function POST(endpoint, actionType, payload) {
  return API(endpoint, actionType, 'POST', payload);
}

function PUT(endpoint, actionType, payload) {
  return API(endpoint, actionType, 'PUT', payload);
}

function PATCH(endpoint, actionType, payload) {
  return API(endpoint, actionType, 'PATCH', payload);
}

function DELETE(endpoint, actionType, payload) {
  return API(endpoint, actionType, 'DELETE', payload);
}

export { GET, POST, PUT, PATCH, DELETE, API, API_CALL };
