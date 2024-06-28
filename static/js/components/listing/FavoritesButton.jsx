import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import PropTypes from "prop-types";

import IconButton from "@mui/material/IconButton";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import Tooltip from "@mui/material/Tooltip";
import Button from "../Button";

import * as Actions from "../../ducks/favorites";

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
        secondary
        onClick={handleSubmit}
        disabled={isSubmitting}
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
        size="small"
        style={{ margin: 0, padding: 0 }}
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
        secondary
        onClick={handleSubmit}
        disabled={isSubmitting}
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
        size="small"
        style={{ margin: 0, padding: 0 }}
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
  textMode: PropTypes.bool,
};

FavoritesButton.defaultProps = {
  textMode: false,
};

export default FavoritesButton;
