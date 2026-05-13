import React from "react";
import CircularProgress from "@mui/material/CircularProgress";

const Spinner = () => (
  <div
    style={{
      position: "fixed",
      display: "flex",
      marginLeft: "auto",
      marginRight: "auto",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
    }}
  >
    <CircularProgress />
  </div>
);

export default Spinner;
