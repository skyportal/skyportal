import React, { useEffect } from "react";
import withRouter from "./withRouter";
import ShiftPage from "./ShiftPage";

const ShiftWithId = ({ route }) => {
  return <ShiftPage route={route} />;
};

export default withRouter(ShiftWithId);
