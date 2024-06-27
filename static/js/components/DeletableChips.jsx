import React from "react";
import PropTypes from "prop-types";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

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
