import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import Link from "@mui/material/Link";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import SearchIcon from "@mui/icons-material/Search";

import UserAvatar from "../user/UserAvatar";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetTopSaversQuery } from "../../ducks/topSavers";
import { useActiveTeam } from "../../ducks/teams";
import WidgetCard, { WidgetEmpty, muted } from "./WidgetCard";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import WidgetLoading from "./WidgetLoading";
import TimespanSelect from "./TimespanSelect";

const defaultPrefs = {
  maxNumSavers: "100",
  sinceDaysAgo: "7",
  candidatesOnly: true,
};

const medals: Record<number, [string, string, string]> = {
  1: ["#FFE48A", "#D4A017", "#8A6508"],
  2: ["#F4F6F8", "#AEB4BA", "#5F666D"],
  3: ["#F2C49B", "#C07A3E", "#6E3F17"],
};

const RankBadge = ({ rank }: { rank: number }) => {
  const medal = medals[rank];
  return (
    <Box
      sx={{
        width: 26,
        height: 26,
        borderRadius: "50%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "0.75rem",
        fontWeight: 700,
        flexShrink: 0,
        fontVariantNumeric: "tabular-nums",
        ...(medal
          ? {
              color: medal[2],
              background: `radial-gradient(circle at 30% 30%, ${medal[0]}, ${medal[1]} 70%)`,
              boxShadow: `0 0 0 2px ${medal[1]}55, 0 2px 4px rgba(0, 0, 0, 0.2)`,
            }
          : { color: "text.secondary" }),
      }}
    >
      {rank}
    </Box>
  );
};

const matches = (saver: any, query: string) =>
  [saver.author.username, saver.author.first_name, saver.author.last_name].some(
    (field) => field?.toLowerCase().includes(query),
  );

const TopSaversList = ({ savers }: { savers: any[] }) => {
  const [query, setQuery] = useState("");
  const visible = savers.filter((saver) =>
    matches(saver, query.trim().toLowerCase()),
  );

  return (
    <>
      <TextField
        id="topSaversSearch"
        placeholder="Search users"
        type="search"
        size="small"
        fullWidth
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: muted(0.5) }} />
              </InputAdornment>
            ),
            sx: { borderRadius: 2 },
          },
        }}
        sx={{ mb: 1 }}
      />
      {visible.map((saver: any) => (
        <Box
          key={saver.author.username}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1.5,
            py: 0.75,
            px: 1,
            mx: -1,
            borderRadius: 2,
            "&:hover": { bgcolor: muted(0.05) },
          }}
        >
          <RankBadge rank={saver.rank} />
          <UserAvatar
            size={30}
            userId={saver.author.id}
            firstName={saver.author.first_name}
            lastName={saver.author.last_name}
            username={saver.author.username}
            gravatarUrl={saver.author.gravatar_url}
            isBot={saver.author?.is_bot || false}
          />
          <Link
            component={RouterLink}
            to={`/user/${saver.author.id}`}
            variant="body2"
            color="inherit"
            noWrap
            sx={{ flex: 1, minWidth: 0, fontWeight: 500 }}
          >
            {saver.author.username}
          </Link>
          <Typography
            variant="body2"
            sx={{
              fontWeight: 600,
              fontVariantNumeric: "tabular-nums",
              whiteSpace: "nowrap",
            }}
          >
            {saver.saves}
            <Typography
              component="span"
              variant="caption"
              color="text.secondary"
              sx={{ ml: 0.5 }}
            >
              saved
            </Typography>
          </Typography>
        </Box>
      ))}
    </>
  );
};

const TopSavers = () => {
  const { activeTeam } = useActiveTeam();
  const { data: savers, isLoading } = useGetTopSaversQuery(
    activeTeam ? { teamID: activeTeam.id } : undefined,
  );
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const prefs = {
    ...defaultPrefs,
    ...((profile?.preferences as any)?.topSavers ?? {}),
  };
  const title = prefs.candidatesOnly ? "Top scanners" : "Top savers";

  return (
    <WidgetCard
      title={title}
      teamScoped
      actions={
        <>
          <TimespanSelect
            value={prefs.sinceDaysAgo}
            onChange={(sinceDaysAgo) =>
              updateUserPreferences({ topSavers: { ...prefs, sinceDaysAgo } })
            }
            testIdPrefix="topSavers"
          />
          <WidgetPrefsDialog
            initialValues={{
              maxNumSavers: prefs.maxNumSavers,
              candidatesOnly: prefs.candidatesOnly,
            }}
            stateBranchName="topSavers"
            title={title}
            onSubmit={updateUserPreferences}
          />
        </>
      }
    >
      {isLoading ? (
        <WidgetLoading />
      ) : !savers?.length ? (
        <WidgetEmpty>No saves in this period.</WidgetEmpty>
      ) : (
        <TopSaversList savers={savers} />
      )}
    </WidgetCard>
  );
};

export default TopSavers;
