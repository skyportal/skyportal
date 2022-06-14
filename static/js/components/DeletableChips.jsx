import React from "react";
import { Chip, Typography } from "@mui/material";
import PropTypes from "prop-types";

const DeletableChips = ({ items, onDelete, title }) => (
  <div>
    <Typography>{title}</Typography>
    {items?.map((item) => (
      <Chip key={item} label={item} onDelete={() => onDelete(item)} />
    ))}
  </div>
);

DeletableChips.propTypes = {
  items: PropTypes.arrayOf(PropTypes.string).isRequired,
  onDelete: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
};

export default DeletableChips;
