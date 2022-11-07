import React from "react";
import PropTypes from "prop-types";

import SpectrumAnalysisForm from "./SpectrumAnalysisForm";
import withRouter from "./withRouter";

const SpectrumAnalysisPage = ({ route }) => (
  <div>
    <div>
      <SpectrumAnalysisForm obj_id={route.id} />
    </div>
  </div>
);

SpectrumAnalysisPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(SpectrumAnalysisPage);
