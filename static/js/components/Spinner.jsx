import React from "react";
import CircularProgress from "@mui/material/CircularProgress";

const Spinner = () => (
  <div
    style={{
      position: "fixed",
      inset: 0,
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      zIndex: 9999,
    }}
  >
    <CircularProgress />
  </div>
);

export default Spinner;
