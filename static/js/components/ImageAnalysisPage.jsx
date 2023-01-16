import React from "react";
import PropTypes from "prop-types";

import ImageAnalysisForm from "./ImageAnalysisForm";
import withRouter from "./withRouter";

const ImageAnalysisPage = ({ route }) => (
  <div>
    <div>
      <ImageAnalysisForm obj_id={route.id} />
    </div>
  </div>
);

ImageAnalysisPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(ImageAnalysisPage);
