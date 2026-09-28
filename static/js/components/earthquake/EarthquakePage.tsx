import { Suspense } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import GetAppIcon from "@mui/icons-material/GetApp";
import { skipToken } from "@reduxjs/toolkit/query";

import { useGetEarthquakeQuery } from "../../ducks/earthquake";
import Spinner from "../Spinner";
import CommentThread from "../comment/CommentThread";
import Reminders from "../Reminders";
import withRouter from "../withRouter";
import EarthquakePredictionForm from "./EarthquakePredictionForm";
import EarthquakeDetectorTables from "./EarthquakeDetectorTables";

interface SectionProps {
  title: string;
  children: React.ReactNode;
}

const Section = ({ title, children }: SectionProps) => (
  <Paper sx={{ p: 2, display: "flex", flexDirection: "column", gap: 2 }}>
    <Typography variant="h6">{title}</Typography>
    {children}
  </Paper>
);

interface EarthquakePageProps {
  route: {
    event_id?: string;
  };
}

const EarthquakePage = ({ route }: EarthquakePageProps) => {
  const { data: earthquake } = useGetEarthquakeQuery(
    route.event_id ?? skipToken,
  ) as { data: any };
  if (!earthquake?.event_id) return <Spinner />;

  const notice = earthquake.notices?.[0];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Paper
        sx={{
          p: 2,
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="h5">{earthquake.event_id}</Typography>
          {notice && (
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              {[notice.date?.replace("T", " "), notice.country]
                .filter(Boolean)
                .join(" · ")}
            </Typography>
          )}
        </Box>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {earthquake.status && <Chip label={earthquake.status} />}
          {notice && (
            <>
              <Chip color="primary" label={`M ${notice.magnitude}`} />
              <Chip
                label={`${notice.lat?.toFixed(4)}, ${notice.lon?.toFixed(4)}`}
              />
              <Chip label={`Depth: ${(notice.depth / 1000).toFixed(1)} km`} />
            </>
          )}
        </Box>
      </Paper>
      <Grid container spacing={2}>
        <Grid
          size={{ xs: 12, lg: 7 }}
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <Section title="Predictions">
            <EarthquakePredictionForm earthquake={earthquake} />
            <EarthquakeDetectorTables
              earthquake={earthquake}
              kind="predictions"
            />
          </Section>
          <Section title="Measurements">
            <EarthquakeDetectorTables
              earthquake={earthquake}
              kind="measurements"
            />
          </Section>
        </Grid>
        <Grid
          size={{ xs: 12, lg: 5 }}
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <Section title="Comments">
            <Suspense fallback={<Spinner />}>
              <CommentThread
                resourceType="earthquake"
                earthquakeID={earthquake.id.toString()}
                earthquakeEventID={earthquake.event_id}
                maxHeightList="350px"
              />
            </Suspense>
          </Section>
          <Reminders
            resourceId={earthquake.id.toString()}
            resourceType="earthquake"
          />
          <Section title="Notices">
            {earthquake.notices?.map((n: any) => (
              <Box
                key={n.id}
                sx={{ display: "flex", alignItems: "center", gap: 1 }}
              >
                <Typography variant="body2">
                  {n.created_at.slice(0, 19).replace("T", " ")}
                </Typography>
                <Tooltip title="Download XML">
                  <IconButton
                    size="small"
                    href={URL.createObjectURL(
                      new Blob([n.content], { type: "text/plain" }),
                    )}
                    download={n.event_id}
                  >
                    <GetAppIcon />
                  </IconButton>
                </Tooltip>
              </Box>
            ))}
          </Section>
        </Grid>
      </Grid>
    </Box>
  );
};

export default withRouter(EarthquakePage);
