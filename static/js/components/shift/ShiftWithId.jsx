import React from "react";
import PropTypes from "prop-types";
import withRouter from "../withRouter";
import ShiftPage from "./ShiftPage";

const ShiftWithId = ({ route }) => <ShiftPage route={route} />;

ShiftWithId.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string.isRequired,
  }).isRequired,
};

export default withRouter(ShiftWithId);
