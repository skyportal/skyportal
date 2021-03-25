import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import PropTypes from "prop-types";

import IconButton from "@material-ui/core/IconButton";
import StarIcon from "@material-ui/icons/Star";
import StarBorderIcon from "@material-ui/icons/StarBorder";
import Button from "@material-ui/core/Button";
import Tooltip from "@material-ui/core/Tooltip";

import * as Actions from "../ducks/favorites";

const ButtonInclude = (sourceID, textMode) => {
  const dispatch = useDispatch();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async () => {
    setIsSubmitting(true);
    await dispatch(Actions.removeFromFavorites(sourceID));
    setIsSubmitting(false);
  };
  if (textMode) {
    return (
      <Button
        onClick={handleSubmit}
        disabled={isSubmitting}
        color="default"
        variant="contained"
        data-testid={`favorites-text-include_${sourceID}`}
      >
        Remove favorite
      </Button>
    );
  }
  return (
    <Tooltip title="click to remove this source from favorites">
      <IconButton
        onClick={handleSubmit}
        data-testid={`favorites-include_${sourceID}`}
        disabled={isSubmitting}
      >
        <StarIcon />
      </IconButton>
    </Tooltip>
  );
};

const ButtonExclude = (sourceID, textMode) => {
  const dispatch = useDispatch();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async () => {
    setIsSubmitting(true);
    await dispatch(Actions.addToFavorites(sourceID));
    setIsSubmitting(false);
  };
  if (textMode) {
    return (
      <Button
        onClick={handleSubmit}
        disabled={isSubmitting}
        color="default"
        variant="contained"
        data-testid={`favorites-text-exclude_${sourceID}`}
      >
        Add favorite
      </Button>
    );
  }
  return (
    <Tooltip title="click to add this source to favorites">
      <IconButton
        onClick={handleSubmit}
        data-testid={`favorites-exclude_${sourceID}`}
        disabled={isSubmitting}
      >
        <StarBorderIcon />
      </IconButton>
    </Tooltip>
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
