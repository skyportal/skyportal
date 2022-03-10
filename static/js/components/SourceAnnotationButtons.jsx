import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";

import Button from "@material-ui/core/Button";
import CircularProgress from "@material-ui/core/CircularProgress";

import * as sourceActions from "../ducks/source";

const SourceAnnotationButtons = ({ source }) => {
  const dispatch = useDispatch();

  const [isSubmittingAnnotationPhotoz, setIsSubmittingAnnotationPhotoz] =
    useState(null);
  const handleAnnotationPhotoz = async (id) => {
    setIsSubmittingAnnotationPhotoz(id);
    await dispatch(sourceActions.fetchPhotoz(id));
    setIsSubmittingAnnotationPhotoz(null);
  };

  const [isSubmittingAnnotationWise, setIsSubmittingAnnotationWise] =
    useState(null);
  const handleAnnotationWise = async (id) => {
    setIsSubmittingAnnotationWise(id);
    await dispatch(sourceActions.fetchWise(id));
    setIsSubmittingAnnotationWise(null);
  };

  return (
    <div>
      {isSubmittingAnnotationPhotoz === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          onClick={() => {
            handleAnnotationPhotoz(source.id);
          }}
          size="small"
          color="primary"
          type="submit"
          variant="outlined"
          data-testid={`photozRequest_${source.id}`}
        >
          Photoz
        </Button>
      )}
      {isSubmittingAnnotationWise === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          onClick={() => {
            handleAnnotationWise(source.id);
          }}
          size="small"
          color="primary"
          type="submit"
          variant="outlined"
          data-testid={`wiseRequest_${source.id}`}
        >
          WISE Colors
        </Button>
      )}
    </div>
  );
};

SourceAnnotationButtons.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string.isRequired,
    ra: PropTypes.number,
    dec: PropTypes.number,
    loadError: PropTypes.oneOfType([PropTypes.string, PropTypes.bool]),
    thumbnails: PropTypes.arrayOf(PropTypes.shape({})),
    redshift: PropTypes.number,
    redshift_error: PropTypes.number,
    groups: PropTypes.arrayOf(PropTypes.shape({})),
    gal_lon: PropTypes.number,
    gal_lat: PropTypes.number,
    dm: PropTypes.number,
    luminosity_distance: PropTypes.number,
    annotations: PropTypes.arrayOf(
      PropTypes.shape({
        origin: PropTypes.string.isRequired,
        data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
      })
    ),
    classifications: PropTypes.arrayOf(
      PropTypes.shape({
        author_name: PropTypes.string,
        probability: PropTypes.number,
        modified: PropTypes.string,
        classification: PropTypes.string,
        id: PropTypes.number,
        obj_id: PropTypes.string,
        author_id: PropTypes.number,
        taxonomy_id: PropTypes.number,
        created_at: PropTypes.string,
      })
    ),
    followup_requests: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    assignments: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    redshift_history: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    color_magnitude: PropTypes.arrayOf(
      PropTypes.shape({
        abs_mag: PropTypes.number,
        color: PropTypes.number,
        origin: PropTypes.string,
      })
    ),
    duplicates: PropTypes.arrayOf(PropTypes.string),
    alias: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
};

export default SourceAnnotationButtons;
