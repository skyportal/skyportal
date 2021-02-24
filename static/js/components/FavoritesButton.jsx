import React from "react";
import { useDispatch, useSelector } from "react-redux";

import PropTypes from "prop-types";

import IconButton from "@material-ui/core/IconButton";
import StarIcon from "@material-ui/icons/Star";
import StarBorderIcon from "@material-ui/icons/StarBorder";
import Button from "@material-ui/core/Button";

import * as Actions from "../ducks/favorites";

const ButtonInclude = (sourceID, textMode) => {
  const dispatch = useDispatch();
  if (textMode) {
    return (
      <Button
        onClick={() => {
          dispatch(Actions.removeFromFavorites(sourceID));
        }}
        color="default"
        variant="contained"
        data-testid={`favorites-text-include_${sourceID}`}
      >
        Remove favorite
      </Button>
    );
  }
  return (
    <IconButton
      onClick={() => {
        dispatch(Actions.removeFromFavorites(sourceID));
      }}
      data-testid={`favorites-include_${sourceID}`}
    >
      <StarIcon />
    </IconButton>
  );
};

const ButtonExclude = (sourceID, textMode) => {
  const dispatch = useDispatch();
  if (textMode) {
    return (
      <Button
        onClick={() => {
          dispatch(Actions.addToFavorites(sourceID));
        }}
        color="default"
        variant="contained"
        data-testid={`favorites-text-exclude_${sourceID}`}
      >
        Add favorite
      </Button>
    );
  }
  return (
    <IconButton
      onClick={() => {
        dispatch(Actions.addToFavorites(sourceID));
      }}
      data-testid={`favorites-exclude_${sourceID}`}
    >
      <StarBorderIcon />
    </IconButton>
  );
};

const FavoritesButton = ({ sourceID, textMode }) => {
  const { favorites } = useSelector((state) => state.favorites);

  if (!sourceID) {
    return null;
  }
  if (favorites.includes(sourceID)) {
    return ButtonInclude(sourceID, textMode);
  }
  return ButtonExclude(sourceID, textMode);
};

FavoritesButton.propTypes = {
  sourceID: PropTypes.string.isRequired,
};

export default FavoritesButton;
