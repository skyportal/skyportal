import messageHandler from "baselayer/MessageHandler";
import * as API from "../API";
import store from "../store";

const FETCH_FAVORITES = "skyportal/FETCH_FAVORITES";
const FETCH_FAVORITES_OK = "skyportal/FETCH_FAVORITES_OK";
const ADD_TO_FAVORITES = "skyportal/ADD_TO_FAVORITES";
const REMOVE_FROM_FAVORITES = "skyportal/REMOVE_FROM_FAVORITES";
const REFRESH_FAVORITES = "skyportal/REFRESH_FAVORITES";

// eslint-disable-next-line import/prefer-default-export
export const fetchFavorites = () =>
  API.GET("/api/listing", FETCH_FAVORITES, { listName: "favorites" });

export const addToFavorites = (source_id) =>
  API.POST("/api/listing", ADD_TO_FAVORITES, {
    list_name: "favorites",
    obj_id: source_id,
  });

export const removeFromFavorites = (source_id) =>
  API.DELETE("/api/listing", REMOVE_FROM_FAVORITES, {
    list_name: "favorites",
    obj_id: source_id,
  });

const reducer = (state = { favorites: [] }, action) => {
  switch (action.type) {
    case FETCH_FAVORITES_OK: {
      const favorites = action.data.map((fav) => fav.obj_id);
      return {
        ...state,
        favorites,
      };
    }
    default:
      return state;
  }
};

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_FAVORITES) {
    dispatch(fetchFavorites());
  }
});

store.injectReducer("favorites", reducer);
