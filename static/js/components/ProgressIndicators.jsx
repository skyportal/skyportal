import * as React from "react";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";

const CircularProgressWithLabel = ({ current, total, percentage }) => (
  <div
    style={{
      display: "flex",
      flexDirection: "column",
      width: "100%",
      height: "100%",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    <CircularProgress
      variant="determinate"
      value={Math.round((current * 100) / total)}
      style={{ width: "100%", height: "100%" }}
    />
    <Box
      sx={{
        top: "25%",
        left: 0,
        bottom: 0,
        right: 0,
        position: "absolute",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {percentage ? (
        <Typography
          variant="caption"
          component="div"
          color="text.secondary"
        >{`${Math.round((current * 100) / total)}%`}</Typography>
      ) : (
        <Typography
          variant="caption"
          component="div"
          color="text.secondary"
        >{`${current}/${total}`}</Typography>
      )}
    </Box>
  </div>
);

CircularProgressWithLabel.defaultProps = {
  current: 0,
  total: 100,
  percentage: true,
};

CircularProgressWithLabel.propTypes = {
  current: PropTypes.number,
  total: PropTypes.number,
  percentage: PropTypes.bool,
};

const TableProgressText = ({ nbItems, status }) => {
  if (nbItems === 0) {
    return null;
  }
  return (
    <div>
      <Typography variant="caption" component="div" color="text.secondary">
        {`${nbItems} ${status}`}
      </Typography>
    </div>
  );
};

TableProgressText.defaultProps = {
  nbItems: 0,
  status: "pending",
};

TableProgressText.propTypes = {
  nbItems: PropTypes.number,
  status: PropTypes.string,
};

export default CircularProgressWithLabel;

export { TableProgressText };
