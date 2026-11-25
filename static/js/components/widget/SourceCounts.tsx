import { CountUp } from "use-count-up";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetSourceCountsQuery } from "../../ducks/sourceCounts";
import { useActiveTeam } from "../../ducks/teams";
import WidgetCard, { TeamBadge } from "./WidgetCard";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import WidgetLoading from "./WidgetLoading";

interface SourceCountsProps {
  sinceDaysAgo?: number;
}

const SourceCounts = ({ sinceDaysAgo }: SourceCountsProps) => {
  const { activeTeam } = useActiveTeam();
  const { data: sourceCounts, isLoading } = useGetSourceCountsQuery(
    activeTeam ? { teamID: activeTeam.id } : undefined,
  );
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const sourceCountPrefs = (profile?.preferences as any)?.sourceCounts || {
    sinceDaysAgo: sinceDaysAgo ? sinceDaysAgo.toString() : "",
  };

  return (
    <WidgetCard
      actions={
        <WidgetPrefsDialog
          initialValues={sourceCountPrefs}
          stateBranchName="sourceCounts"
          title="New sources"
          onSubmit={updateUserPreferences}
        />
      }
      bodySx={{ p: 2 }}
    >
      {isLoading ? (
        <WidgetLoading />
      ) : (
        <Box
          id="sourceCountsWidget"
          className="dragHandle"
          sx={{
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-end",
            cursor: "grab",
            "&:active": { cursor: "grabbing" },
          }}
        >
          <Typography
            sx={{
              fontSize: "2.5rem",
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: "-0.02em",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            <CountUp
              {...({ id: "sourceCounter" } as any)}
              isCounting
              end={sourceCounts?.count ?? 0}
              duration={1.0}
            />
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            New sources
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
            <Typography variant="caption" color="text.secondary">
              Last {sourceCounts?.sinceDaysAgo} days
            </Typography>
            <TeamBadge />
          </Box>
        </Box>
      )}
    </WidgetCard>
  );
};

export default SourceCounts;
