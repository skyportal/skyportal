import CircularProgress from "@mui/material/CircularProgress";
import React from "react";
import PropTypes from "prop-types";
import ScanningPageCandidateAnnotations from "./ScanningPageCandidateAnnotations";

/**
 * Container for the candidate auto annotations.
 */
const CandidateAutoannotations = ({ annotations, filterGroups }) => (
  <div>
    {!annotations ? (
      <div>
        <CircularProgress />
      </div>
    ) : (
      <div
        style={{
          overflowWrap: "break-word"
        }}
      >
        {annotations && (
          <ScanningPageCandidateAnnotations
            annotations={annotations}
            filterGroups={filterGroups || []}
          />
        )}
      </div>
    )}
  </div>
);

CandidateAutoannotations.propTypes = {
  annotations: PropTypes.arrayOf(PropTypes.shape({})),
  filterGroups: PropTypes.arrayOf(PropTypes.shape({})),
};

CandidateAutoannotations.defaultProps = {
  annotations: null,
  filterGroups: [],
};

export default CandidateAutoannotations;
