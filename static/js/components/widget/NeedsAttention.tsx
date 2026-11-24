/**
 * Open obligations, as opposed to things that merely happened.
 *
 * The news feed is a record of events: it scrolls, and an item that needed
 * answering looks exactly like one that did not. This one does not scroll
 * away: an object you have scheduled that another group has scheduled too,
 * which is worth reconciling before the night rather than after it.
 */
import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";

import { useGetDuplicateSchedulingQuery } from "../../ducks/duplicateScheduling";
import WidgetCard, { WidgetEmpty, muted } from "./WidgetCard";
import WidgetLoading from "./WidgetLoading";

const NeedsAttention = () => {
  // No websocket for this one: a clash is created by a group you are not in,
  // and REFRESH_FOLLOWUP_REQUESTS only reaches whoever made the request.
  // Broadcasting it to everyone would have every client refetch on every
  // request, so poll instead -- observing plans change over minutes, not
  // seconds.
  const { data: collisions, isLoading } = useGetDuplicateSchedulingQuery(
    undefined,
    { pollingInterval: 5 * 60 * 1000 },
  );

  const clashes = collisions ?? [];

  return (
    <WidgetCard title="Needs your attention">
      {isLoading ? (
        <WidgetLoading />
      ) : clashes.length === 0 ? (
        <WidgetEmpty>Nothing waiting on you.</WidgetEmpty>
      ) : (
        clashes.map((clash: any) => (
          <Box
            key={`clash-${clash.obj_id}-${clash.group_name}-${clash.instrument_name}`}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              py: 1,
              px: 1,
              mx: -1,
              borderRadius: 2,
              "&:hover": { bgcolor: muted(0.05) },
            }}
          >
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                flexShrink: 0,
                bgcolor: "warning.main",
              }}
            />
            <Box sx={{ minWidth: 0 }}>
              <Link
                component={RouterLink}
                to={`/source/${clash.obj_id}`}
                variant="body2"
                sx={{ fontWeight: 600 }}
              >
                {clash.obj_id}
              </Link>
              <Typography variant="body2" color="text.secondary">
                Also scheduled by {clash.group_name} on {clash.instrument_name}
              </Typography>
            </Box>
          </Box>
        ))
      )}
    </WidgetCard>
  );
};

export default NeedsAttention;
