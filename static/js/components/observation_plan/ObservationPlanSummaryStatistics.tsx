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

  if (!summaryStatistics || summaryStatistics?.length === 0) {
    return (
      <div>
        <div>
          <CircularProgress />
        </div>
      </div>
    );
  }

  const stats = summaryStatistics[0]!.statistics;

  return (
    <div>
      <div>
        <ul>
          <li> Number of Observations: {stats.num_observations} </li>
          <li> Delay from Trigger: {stats.dt} </li>
          <li> Start of Observations: {stats.start_observation} </li>
          <li> Unique filters: {stats.unique_filters?.join(", ")} </li>
          <li> Total time [s]: {stats.total_time} </li>
          <li> Probability: {stats.probability?.toFixed(3)} </li>
          <li> Area [sq. deg.]: {stats.area?.toFixed(1)} </li>
        </ul>
      </div>
    </div>
  );
};

export default ObservationPlanSummaryStatistics;
