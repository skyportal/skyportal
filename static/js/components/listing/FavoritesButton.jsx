import React from "react";
import { useDispatch, useSelector } from "react-redux";

import PropTypes from "prop-types";

import IconButton from "@mui/material/IconButton";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import Tooltip from "@mui/material/Tooltip";

import * as Actions from "../../ducks/favorites";

const FavoritesButton = ({ sourceID }) => {
  const dispatch = useDispatch();
  const { favorites } = useSelector((state) => state.favorites);

  if (!sourceID) return null;

  const isCheck = favorites.includes(sourceID);
  const handleSubmit = () => {
    dispatch(
      isCheck
        ? Actions.removeFromFavorites(sourceID)
        : Actions.addToFavorites(sourceID),
    );
  };
  return (
    <Tooltip
      title={
        isCheck
          ? "click to remove this source from favorites"
          : "click to add this source to favorites"
      }
    >
      <IconButton
        onClick={handleSubmit}
        data-testid={
          isCheck
            ? `favorites-include_${sourceID}`
            : `favorites-exclude_${sourceID}`
        }
        size="small"
        color={isCheck ? "warning" : "default"}
        style={{ margin: 0, padding: 0 }}
      >
        {isCheck ? <StarIcon /> : <StarBorderIcon />}
      </IconButton>
    </Tooltip>
  );
};

FavoritesButton.propTypes = {
  sourceID: PropTypes.string.isRequired,
};

export default FavoritesButton;
