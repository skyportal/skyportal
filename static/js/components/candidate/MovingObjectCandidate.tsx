import Box from "@mui/material/Box";
import MuiLink from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import { useIsReadOnly } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import type { Group } from "../../types";
import ThumbnailList from "../thumbnail/ThumbnailList";
import VegaPhotometry from "../plot/VegaPhotometry";
import TrackCandidateSummary from "../moving_object/TrackCandidateSummary";
import RejectButton from "../RejectButton";
import SaveCandidateButton from "./SaveCandidateButton";
import { flattenAnnotationData } from "./annotationValue";

const ALERT_CUTOUTS = ["new", "ref", "sub"];
const HIDDEN_KEYS = new Set(["designation"]);

const formatValue = (value: unknown) =>
  typeof value === "number" && !Number.isInteger(value)
    ? String(Number(value.toFixed(3)))
    : String(value);

const annotationFacts = (annotations: any[]): [string, string][] => {
  const facts = new Map<string, string>();
  for (const annotation of annotations) {
    for (const [key, value] of flattenAnnotationData(annotation.data)) {
      if (
        HIDDEN_KEYS.has(key) ||
        value === null ||
        typeof value === "object" ||
        facts.has(key)
      )
        continue;
      facts.set(key, formatValue(value));
    }
  }
  return [...facts];
};

interface MovingObjectCandidateProps {
  candidate: any;
  trackId: string | null;
  filterGroups: Group[];
  index: number;
  totalMatches: number;
}

const MovingObjectCandidate = ({
  candidate,
  trackId,
  filterGroups,
  index,
  totalMatches,
}: MovingObjectCandidateProps) => {
  const isReadOnly = useIsReadOnly();
  const { data: groups } = useGetGroupsQuery();
  const savedGroupIds = candidate.saved_groups?.map((g: any) => g.id) ?? [];
  const unsaved = (list: Group[]) =>
    list.filter((g) => !savedGroupIds.includes(g.id));
  const unsavedUserGroups = unsaved(groups?.userAccessible ?? []);
  const track = candidate.broker_id != null ? trackId : null;
  const name = track ?? candidate.mpc_name ?? candidate.id;
  const lastDetected = candidate.last_detected_at
    ? String(candidate.last_detected_at).slice(0, 16).replace("T", " ")
    : null;
  const facts = track ? [] : annotationFacts(candidate.annotations ?? []);

  return (
    <Paper
      variant="outlined"
      data-testid={`moving-object-${index}`}
      sx={{
        borderWidth: 2,
        mb: 2,
        p: 1.5,
        display: "grid",
        gap: 2,
        alignItems: "start",
        gridTemplateColumns: {
          xs: "100%",
          md: track ? "18rem 1fr" : "18rem 1fr 1fr",
        },
      }}
    >
      <ThumbnailList
        ra={candidate.ra}
        dec={candidate.dec}
        thumbnails={candidate.thumbnails}
        displayTypes={ALERT_CUTOUTS}
        size="100%"
        maxSize="6rem"
        titleSize="0.7rem"
        useGrid={false}
        columns={3}
        noMargin
        footer={
          <Typography variant="body2" sx={{ fontWeight: "bold" }}>
            {`${index}/${totalMatches}`}
          </Typography>
        }
      />
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: 1,
          }}
        >
          <MuiLink
            href={`/source/${candidate.id}`}
            target="_blank"
            rel="noreferrer"
            sx={{ fontWeight: "bold", fontSize: "1.05rem" }}
          >
            {name}
          </MuiLink>
          {track && (
            <Typography variant="body2" color="text.secondary">
              {candidate.id}
            </Typography>
          )}
          {lastDetected && (
            <Typography variant="body2" color="text.secondary">
              last seen {lastDetected} UTC
            </Typography>
          )}
          <Box sx={{ ml: "auto", display: "flex", gap: 0.5 }}>
            {!isReadOnly && unsavedUserGroups.length > 0 && (
              <SaveCandidateButton
                candidate={candidate}
                userGroups={unsavedUserGroups}
                filterGroups={unsaved(filterGroups)}
              />
            )}
            <RejectButton objID={candidate.id} />
          </Box>
        </Box>
        {track && (
          <TrackCandidateSummary
            trackId={track}
            brokerId={candidate.broker_id}
            objId={candidate.id}
            showId={false}
          />
        )}
        {facts.length > 0 && (
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              columnGap: 2,
              rowGap: 0.25,
            }}
          >
            {facts.map(([key, value]) => (
              <Typography key={key} variant="body2" color="text.secondary">
                {key}{" "}
                <Box
                  component="span"
                  sx={{ color: "text.primary", fontWeight: 600 }}
                >
                  {value}
                </Box>
              </Typography>
            ))}
          </Box>
        )}
      </Box>
      {!track && (
        <VegaPhotometry
          sourceId={candidate.id}
          style={{ width: "100%", height: "14rem" }}
          defaultShowUpperLimits={false}
          renderer="canvas"
        />
      )}
    </Paper>
  );
};

export default MovingObjectCandidate;
