import { Fragment } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

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
    return "Only available for completed requests.";
  }

  if (!summaryStatistics?.length) return <CircularProgress />;

  const stats = summaryStatistics[0]!.statistics;

  const rows: [string, React.ReactNode][] = [
    ["Observations", stats.num_observations],
    ["Delay from trigger", stats.dt],
    ["Start", stats.start_observation],
    ["Filters", stats.unique_filters?.join(", ")],
    ["Total time [s]", stats.total_time],
    ["Probability", stats.probability?.toFixed(3)],
    ["Area [sq. deg.]", stats.area?.toFixed(1)],
  ];

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "auto 1fr",
        columnGap: 1.5,
        rowGap: 0.25,
      }}
    >
      {rows.map(([label, value]) => (
        <Fragment key={label}>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {label}
          </Typography>
          <Typography variant="caption">{value}</Typography>
        </Fragment>
      ))}
    </Box>
  );
};

export default ObservationPlanSummaryStatistics;
