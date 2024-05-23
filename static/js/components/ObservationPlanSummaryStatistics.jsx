import React from "react";
import PropTypes from "prop-types";

import CircularProgress from "@mui/material/CircularProgress";

const ObservationPlanSummaryStatistics = ({ observationplanRequest }) => {
  const summaryStatistics =
    observationplanRequest?.observation_plans[0]?.statistics;

  if (
    !["complete", "submitted to telescope queue"].includes(
      observationplanRequest?.status,
    )
  ) {
    return (
      <div>
        <p>Only available for completed requests.</p>
      </div>
    );
  }

  return (
    <div>
      {!summaryStatistics || summaryStatistics?.length === 0 ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div>
          <ul>
            <li>
              {" "}
              Number of Observations:{" "}
              {summaryStatistics[0].statistics.num_observations}{" "}
            </li>
            <li> Delay from Trigger: {summaryStatistics[0].statistics.dt} </li>
            <li>
              {" "}
              Start of Observations:{" "}
              {summaryStatistics[0].statistics.start_observation}{" "}
            </li>
            <li>
              {" "}
              Unique filters:{" "}
              {summaryStatistics[0].statistics.unique_filters?.join(", ")}{" "}
            </li>
            <li>
              {" "}
              Total time [s]: {summaryStatistics[0].statistics.total_time}{" "}
            </li>
            <li>
              {" "}
              Probability:{" "}
              {summaryStatistics[0].statistics.probability?.toFixed(3)}{" "}
            </li>
            <li>
              {" "}
              Area [sq. deg.]:{" "}
              {summaryStatistics[0].statistics.area?.toFixed(1)}{" "}
            </li>
          </ul>
        </div>
      )}
    </div>
  );
};

ObservationPlanSummaryStatistics.propTypes = {
  observationplanRequest: PropTypes.shape({
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
              dt: PropTypes.number,
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
