import React from "react";
import PropTypes from "prop-types";
import MuiPaper from "@mui/material/Paper";

const Paper = ({ noPadding, sx, ...props }) => {
  return (
    <MuiPaper
      sx={{
        ...(noPadding ? {} : { padding: "1rem" }),
        ...sx,
      }}
      {...props}
    />
  );
};

Paper.propTypes = {
  noPadding: PropTypes.bool,
  sx: PropTypes.shape({}),
};

export default Paper;
