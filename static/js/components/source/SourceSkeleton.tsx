import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import Skeleton from "@mui/material/Skeleton";
import { useTheme } from "@mui/material/styles";

import { SlowLoadNotice } from "../Spinner";

interface SourceSkeletonProps {
  /** Known from the route before any data arrives, so it can be shown at once. */
  objId: string;
}

/**
 * The source page's layout, drawn before its data arrives.
 *
 * The object's name is known from the URL, so there is no reason to show
 * nothing at all: the page keeps its shape and fills in, rather than sitting
 * behind a whole-page spinner that is indistinguishable from a hang.
 */
const SourceSkeleton = ({ objId }: SourceSkeletonProps) => {
  const theme = useTheme();

  return (
    <Grid container spacing={1.5}>
      <Grid size={12}>
        <Paper style={{ padding: "0.5rem" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              columnGap: "0.25rem",
              marginBottom: "0.25rem",
            }}
          >
            <Skeleton variant="circular" width={22} height={22} />
            <h6
              style={{
                lineHeight: "1em",
                fontSize: "200%",
                fontWeight: 900,
                display: "inline-block",
                margin: 0,
                color:
                  theme.palette.mode === "dark"
                    ? theme.palette.secondary.main
                    : theme.palette.primary.main,
              }}
            >
              {objId}
            </h6>
          </div>

          {/* coordinates, redshift, TNS name */}
          <Skeleton variant="text" width="60%" height={24} />
          <Skeleton variant="text" width="45%" height={24} />

          {/* the action buttons (search alerts, finding chart, ...) */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "0.5rem",
              margin: "0.75rem 0",
            }}
          >
            {[...Array(6)].map((_, index) => (
              <Skeleton
                key={`button-${index}`}
                variant="rounded"
                width={110}
                height={30}
              />
            ))}
          </div>

          {/* cutouts */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {[...Array(5)].map((_, index) => (
              <Skeleton
                key={`thumbnail-${index}`}
                variant="rounded"
                width={150}
                height={150}
              />
            ))}
          </div>
        </Paper>
      </Grid>

      <Grid size={12}>
        <Paper style={{ padding: "0.5rem" }}>
          <Skeleton variant="text" width="12rem" height={28} />
          <Skeleton variant="rounded" width="100%" height="20rem" />
        </Paper>
      </Grid>

      <Grid size={12}>
        <SlowLoadNotice />
      </Grid>
    </Grid>
  );
};

export default SourceSkeleton;
