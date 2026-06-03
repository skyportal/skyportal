import CircularProgress from "@mui/material/CircularProgress";

interface ObservationPlanSummaryStatisticsProps {
  observationplanRequest: {
    id?: number;
    requester?: {
      id?: number;
      username?: string;
    };
    instrument?: {
      id?: number;
      name?: string;
    };
    status?: string;
    allocation?: {
      group?: {
        name?: string;
      };
    };
    observation_plans?: {
      statistics?: {
        statistics: {
          id?: number;
          probability?: number;
          area?: number;
          num_observations?: number;
          dt?: string;
          total_time?: number;
          start_observation?: string;
          unique_filters?: string[];
        };
      }[];
    }[];
  };
}

const ObservationPlanSummaryStatistics = ({
  observationplanRequest,
}: ObservationPlanSummaryStatisticsProps) => {
  const summaryStatistics =
    observationplanRequest?.observation_plans?.[0]?.statistics;

  if (
    !["complete", "submitted to telescope queue"].includes(
      observationplanRequest?.status as string,
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

export default ObservationPlanSummaryStatistics;
