import React from "react";
import PropTypes from "prop-types";
import VegaPhotometry from "../vega/VegaPhotometry";

/**
 * Photometry plot displayed in the Candidate card
 */
const CandidatePhotometry = ({ sourceId }) => (
  <div>
    <VegaPhotometry
      sourceId={sourceId}
      style={{
        width: "68%",
        height: "100%",
        minHeight: "18rem",
        maxHeight: "18rem"
      }}
    />
  </div>
);

CandidatePhotometry.propTypes = {
  sourceId: PropTypes.string.isRequired,
};

export default CandidatePhotometry;
