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
            'error')
        );
      }
      dispatch({ type: API_CALL, parameters });
      try {
        const response = await fetch(endpoint, fetchInit);
        if (response.status !== 200) {
          throw new Error(
            `Could not fetch data from server (${response.status})`
          );
        }

        const json = await response.json();
        if (json.status === "success") {
          dispatch({ type: `${actionType}_OK`, ...json });
          return json.data;
        } else {
          /* In case of an error, dispatch an action that contains
             every piece of information we have about the request, including
             JSON args, and the response that came back from the server.

             This information can be used in a reducer to set an error message.
          */
          dispatch({ type: `${actionType}_FAIL`, parameters, response: json });
          throw json.message;
        }
      } catch (error) {
        dispatch({ type: `${actionType}_FAIL`, parameters, error });
        return dispatch(showNotification(`API error: ${error}`, 'error'));
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

function DELETE(endpoint, actionType, payload) {
  return API(endpoint, actionType, 'DELETE', payload);
}

export { GET, POST, PUT, DELETE, API, API_CALL };
