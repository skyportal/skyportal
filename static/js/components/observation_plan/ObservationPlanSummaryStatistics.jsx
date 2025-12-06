import React from "react";
import PropTypes from "prop-types";

import CircularProgress from "@mui/material/CircularProgress";

const ObservationPlanSummaryStatistics = ({ observationPlanRequest }) => {
  if (!observationPlanRequest?.observation_plans.length)
    return <p>No observation plans available.</p>;
  const statistics = observationPlanRequest?.observation_plans[0]?.statistics;
  const statistic = statistics?.length ? statistics[0] : null;

  if (
    !["complete", "submitted to telescope queue"].includes(
      observationPlanRequest?.status,
    )
  ) {
    return <p>Only available for completed requests.</p>;
  }

  return !statistic ? (
    <CircularProgress />
  ) : (
    <ul>
      <li>Number of Observations: {statistic.statistics.num_observations}</li>
      <li>Delay from Trigger: {statistic.statistics.dt}</li>
      <li>Start of Observations: {statistic.statistics.start_observation}</li>
      <li>Unique filters: {statistic.statistics.unique_filters?.join(", ")}</li>
      <li>Total time [s]: {statistic.statistics.total_time}</li>
      <li>Probability: {statistic.statistics.probability?.toFixed(3)}</li>
      <li>Area [sq. deg.]: {statistic.statistics.area?.toFixed(1)}</li>
    </ul>
  );
};

ObservationPlanSummaryStatistics.propTypes = {
  observationPlanRequest: PropTypes.shape({
    id: PropTypes.number,
    requester: PropTypes.shape({
      id: PropTypes.number,
      username: PropTypes.string,
    }),
    instrument: PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
    }),
    status: PropTypes.string,
    allocation: PropTypes.shape({
      group: PropTypes.shape({
        name: PropTypes.string,
      }),
    }),
    observation_plans: PropTypes.arrayOf(
      PropTypes.shape({
        statistics: PropTypes.arrayOf(
          PropTypes.shape({
            statistics: PropTypes.shape({
              id: PropTypes.number,
              probability: PropTypes.number,
              area: PropTypes.number,
              num_observations: PropTypes.number,
              dt: PropTypes.string,
              total_time: PropTypes.number,
              start_observation: PropTypes.string,
              unique_filters: PropTypes.arrayOf(PropTypes.string),
            }),
          }),
        ),
      }),
    ),
  }).isRequired,
};

export default ObservationPlanSummaryStatistics;
