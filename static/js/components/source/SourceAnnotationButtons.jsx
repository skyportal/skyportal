import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";

import CircularProgress from "@mui/material/CircularProgress";
import Button from "../Button";

import SourceAnnotationButtonPlugins from "./SourceAnnotationButtonPlugins";

import * as sourceActions from "../../ducks/source";

const SourceAnnotationButtons = ({ source }) => {
  const dispatch = useDispatch();

  const [isSubmittingAnnotationGaia, setIsSubmittingAnnotationGaia] =
    useState(null);
  const handleAnnotationGaia = async (id) => {
    setIsSubmittingAnnotationGaia(id);
    await dispatch(sourceActions.fetchGaia(id));
    setIsSubmittingAnnotationGaia(null);
  };

  const [isSubmittingAnnotationWise, setIsSubmittingAnnotationWise] =
    useState(null);
  const handleAnnotationWise = async (id) => {
    setIsSubmittingAnnotationWise(id);
    await dispatch(sourceActions.fetchWise(id));
    setIsSubmittingAnnotationWise(null);
  };

  const [isSubmittingAnnotationQuasar, setIsSubmittingAnnotationQuasar] =
    useState(null);
  const handleAnnotationQuasar = async (id) => {
    setIsSubmittingAnnotationQuasar(id);
    await dispatch(sourceActions.fetchVizier(id, "VII/290"));
    setIsSubmittingAnnotationQuasar(null);
  };

  const [isSubmittingAnnotationGalex, setIsSubmittingAnnotationGalex] =
    useState(null);
  const handleAnnotationGalex = async (id) => {
    setIsSubmittingAnnotationGalex(id);
    await dispatch(sourceActions.fetchVizier(id, "II/335/galex_ais"));
    setIsSubmittingAnnotationGalex(null);
  };

  const [isSubmittingAnnotationPhotoz, setIsSubmittingAnnotationPhotoz] =
    useState(null);
  const handleAnnotationPhotoz = async (id) => {
    setIsSubmittingAnnotationPhotoz(id);
    await dispatch(sourceActions.fetchPhotoz(id));
    setIsSubmittingAnnotationPhotoz(null);
  };

  const [isSubmittingAnnotationPS1, setIsSubmittingAnnotationPS1] =
    useState(null);
  const handleAnnotationPS1 = async (id) => {
    setIsSubmittingAnnotationPS1(id);
    await dispatch(sourceActions.fetchPS1(id));
    setIsSubmittingAnnotationPS1(null);
  };

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        flexDirection: "row",
        gap: "0.5rem",
      }}
    >
      {isSubmittingAnnotationGaia === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationGaia(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`gaiaRequest_${source.id}`}
        >
          Gaia
        </Button>
      )}
      {isSubmittingAnnotationWise === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationWise(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`wiseRequest_${source.id}`}
        >
          WISE Colors
        </Button>
      )}
      {isSubmittingAnnotationQuasar === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationQuasar(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`quasarRequest_${source.id}`}
        >
          Million Quasar
        </Button>
      )}
      {isSubmittingAnnotationGalex === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationGalex(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`galexRequest_${source.id}`}
        >
          GALEX
        </Button>
      )}
      {isSubmittingAnnotationPhotoz === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationPhotoz(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`photozRequest_${source.id}`}
        >
          Photoz
        </Button>
      )}
      {isSubmittingAnnotationPS1 === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationPS1(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`ps1Request_${source.id}`}
        >
          PS1
        </Button>
      )}
      <SourceAnnotationButtonPlugins source={source} />
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
      }),
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
      }),
    ),
    followup_requests: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    assignments: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    redshift_history: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    color_magnitude: PropTypes.arrayOf(
      PropTypes.shape({
        abs_mag: PropTypes.number,
        color: PropTypes.number,
        origin: PropTypes.string,
      }),
    ),
    duplicates: PropTypes.arrayOf(PropTypes.string),
    alias: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
};

export default SourceAnnotationButtons;
