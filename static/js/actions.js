export const API_CALL = 'skyportal/API_CALL';
export const RECEIVE_SOURCES = 'skyportal/RECEIVE_SOURCES';
export const RECEIVE_LOADED_SOURCE = 'skyportal/RECEIVE_LOADED_SOURCE';
export const RECEIVE_LOADED_SOURCE_FAIL = 'skyportal/RECEIVE_LOADED_SOURCE_FAIL';
export const RECEIVE_SOURCE_PLOT = 'skyportal/RECEIVE_SOURCE_PLOT';
export const RECEIVE_SOURCE_PLOT_FAIL = 'skyportal/RECEIVE_SOURCE_PLOT_FAIL';

import { showNotification } from 'baselayer/components/Notifications';


let API = (endpoint, receiveActionType, args) => (
  async (dispatch) => {
    dispatch({type: API_CALL, endpoint, args});
    try {
      let response = await fetch(endpoint, {credentials: 'same-origin'});
      if (response.status != 200) {
        throw `Could not fetch data from server (${response.status})`;
      }

      let json = await response.json();
      if (json.status == "success") {
        dispatch({type: receiveActionType, ...json});
        return json["data"];
      } else {
        /* In case of an error, dispatch an action that contains
           every piece of information we have about the request, including
           JSON args, and the response that came back from the server.

           This information can be used in a reducer to set an error message.
         */
        dispatch({type: `${receiveActionType}_FAIL`, endpoint, args, response: json})
        throw json["message"];
      }
    }
    catch (error) {
      dispatch(showNotification(error, 'error'));
    }
  }
)

function fetchSource(id) {
  return API(`/sources/${id}`, RECEIVE_LOADED_SOURCE)
}

function fetchSources() {
  return API('/sources', RECEIVE_SOURCES)
}

function hydrate() {
  return (dispatch) => {
    dispatch(fetchSources());
  }
}

export { fetchSources, fetchSource, hydrate, API };
