import React from "react";
import { useDispatch, useSelector } from "react-redux";

import PropTypes from "prop-types";

import IconButton from "@material-ui/core/IconButton";
import StarIcon from "@material-ui/icons/Star";
import StarBorderIcon from "@material-ui/icons/StarBorder";

import * as Actions from "../ducks/favorites";

const FavoritesButton = ({ sourceID }) => {
  const { favorites } = useSelector((state) => state.favorites);
  const dispatch = useDispatch();

  if (!sourceID) {
    return null;
  }
  if (favorites.includes(sourceID)) {
    return (
      <IconButton
        onClick={() => {
          dispatch(Actions.removeFromFavorites(sourceID));
        }}
      >
        <StarIcon />
      </IconButton>
    );
  }

  return (
    <IconButton
      onClick={() => {
        dispatch(Actions.addToFavorites(sourceID));
      }}
    >
      <StarBorderIcon />
    </IconButton>
  );
};

FavoritesButton.propTypes = {
  sourceID: PropTypes.string.isRequired,
};

export default FavoritesButton;
