import React from "react";
import { useDispatch, useSelector } from "react-redux";

import PropTypes from "prop-types";

import IconButton from "@material-ui/core/IconButton";
import StarIcon from "@material-ui/icons/Star";
import StarBorderIcon from "@material-ui/icons/StarBorder";

import * as Actions from "../ducks/favorites";

const FavoritesButton = ({ source_id }) => {
  const { favorites } = useSelector((state) => state.favorites);
  const dispatch = useDispatch();

  if (!source_id) {
    return null;
  }
  if (favorites.includes(source_id)) {
    return (
      <IconButton
        onClick={() => {
          dispatch(Actions.removeFromFavorites(source_id));
        }}
      >
        <StarIcon />
      </IconButton>
    );
  }

  return (
    <IconButton
      onClick={() => {
        dispatch(Actions.addToFavorites(source_id));
      }}
    >
      <StarBorderIcon />
    </IconButton>
  );
};

FavoritesButton.propTypes = {
  source_id: PropTypes.string.isRequired,
};

export default FavoritesButton;
