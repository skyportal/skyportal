import React from "react";
import PropTypes from "prop-types";

import LightcurveFitForm from "./LightcurveFitForm";
import LightcurveFitLists from "./LightcurveFitLists";
import withRouter from "./withRouter";

const LightcurveFitPage = ({ route }) => (
  <div>
    <div>
      <LightcurveFitForm obj_id={route.id} />
    </div>
    <div>
      <LightcurveFitLists obj_id={route.id} />
    </div>
  </div>
);

LightcurveFitPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(LightcurveFitPage);
