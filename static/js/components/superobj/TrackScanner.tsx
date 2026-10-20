import { Fragment, useState } from "react";
import { Link } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TablePagination from "@mui/material/TablePagination";
import Typography from "@mui/material/Typography";

import { useGetGroupsQuery } from "../../ducks/groups";
import {
  useGetSuperObjsQuery,
  type SuperObj,
  type SuperObjEpoch,
} from "../../ducks/superObjs";
import SegmentedControl from "../SegmentedControl";
import { SURVEY_FIELD_OF_VIEW_ARCSEC } from "../thumbnail/ThumbnailList";
import SaveTrackButton from "./SaveTrackButton";

const CUTOUT_TYPES = ["new", "ref", "sub"] as const;
const CUTOUT_LABELS: Record<string, string> = {
  new: "Science",
  ref: "Template",
  sub: "Difference",
};

const TRACK_ANNOTATION_ORIGIN = "boom:track";

const NEO_DIGEST2_THRESHOLD = 65;

const trackOrbit = (track: SuperObj): Record<string, unknown> => {
  for (const epoch of track.objs) {
    for (const annotation of epoch.annotations || []) {
      if (annotation.origin === TRACK_ANNOTATION_ORIGIN) {
        return annotation.data || {};
      }
    }
  }
  return {};
};

const num = (value: unknown, digits = 3) =>
  typeof value === "number" ? value.toFixed(digits) : null;

// Keyed on position, not Obj id: a detection shared by tracklets arrives as distinct Objs.
const distinctEpochs = (track: SuperObj): SuperObjEpoch[] => {
  const seen = new Set<string>();
  return track.objs.filter((epoch) => {
    const key = `${epoch.ra?.toFixed(7)},${epoch.dec?.toFixed(7)}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
};

const cutout = (epoch: SuperObjEpoch, type: string) =>
  (epoch.thumbnails || []).find((t) => t.type === type && t.public_url);

const epochSurvey = (epoch: SuperObjEpoch) =>
  (epoch.thumbnails || []).find(
    (t) => t.survey && (CUTOUT_TYPES as readonly string[]).includes(t.type),
  )?.survey ?? null;

const Cutout = ({
  epoch,
  type,
  zoom,
}: {
  epoch: SuperObjEpoch;
  type: string;
  zoom: number;
}) => {
  const url = cutout(epoch, type)?.public_url;
  return (
    <Box
      sx={{
        width: 100,
        height: 100,
        borderRadius: 0.5,
        overflow: "hidden",
        bgcolor: url && zoom !== 1 ? "black" : "action.hover",
      }}
    >
      {url && (
        <img
          src={url}
          alt={`${CUTOUT_LABELS[type] ?? type} cutout for ${epoch.id}`}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            ...(zoom !== 1 ? { transform: `scale(${zoom})` } : {}),
          }}
        />
      )}
    </Box>
  );
};

const TrackRow = ({
  track,
  userGroups,
}: {
  track: SuperObj;
  userGroups: { id: number; name: string; nickname?: string | null }[];
}) => {
  const orbit = trackOrbit(track);
  const digest2 = orbit["digest2"];
  const isNeo = typeof digest2 === "number" && digest2 >= NEO_DIGEST2_THRESHOLD;
  const name = track.name || `Track ${track.id}`;

  const epochs = distinctEpochs(track);
  const repeats = track.objs.length - epochs.length;

  const [sameScale, setSameScale] = useState(false);
  const fieldOfView = (epoch: SuperObjEpoch) =>
    SURVEY_FIELD_OF_VIEW_ARCSEC[epochSurvey(epoch) ?? ""];
  const fieldsOfView = [
    ...new Set(epochs.map(fieldOfView).filter(Boolean)),
  ] as number[];
  const widestFieldOfView = Math.max(...fieldsOfView);
  const zoomOf = (epoch: SuperObjEpoch) => {
    const fov = fieldOfView(epoch);
    return sameScale && fov ? fov / widestFieldOfView : 1;
  };

  const facts: [string, string | null][] = [
    ["Detections", String(epochs.length)],
    ["Tracklets", num(orbit["n_tracklets"], 0)],
    ["Nights", num(orbit["nights"], 0)],
    ["Residual", num(orbit["fit_residual_arcsec"], 2)],
    ["r (au)", num(orbit["hypothesis_r_au"], 2)],
    ["dr/dt (au/d)", num(orbit["hypothesis_rdot_au_per_day"], 4)],
    ["digest2", num(digest2, 1)],
  ];
  const notes = [
    Object.keys(orbit).length === 0 && "No orbit fit",
    repeats > 0 &&
      `${repeats} repeated detection${repeats === 1 ? "" : "s"} merged`,
  ].filter((note): note is string => Boolean(note));

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          {name}
        </Typography>
        {isNeo && <Chip size="small" color="warning" label="NEO candidate" />}
        <Box sx={{ ml: "auto" }}>
          <SaveTrackButton
            trackName={name}
            epochs={epochs}
            userGroups={userGroups}
          />
        </Box>
      </Box>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          columnGap: 2.5,
          rowGap: 0.5,
          mt: 0.25,
          mb: 1.5,
        }}
      >
        {facts
          .filter(([, value]) => value !== null)
          .map(([label, value]) => (
            <Typography key={label} variant="body2" color="text.secondary">
              {label}{" "}
              <Box
                component="span"
                sx={{ color: "text.primary", fontWeight: 600 }}
              >
                {value}
              </Box>
            </Typography>
          ))}
        {notes.map((note) => (
          <Typography key={note} variant="body2" color="text.secondary">
            {note}
          </Typography>
        ))}
      </Box>

      <Box sx={{ overflowX: "auto", pb: 0.5 }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: `auto repeat(${epochs.length}, 100px)`,
            columnGap: 1,
            rowGap: 0.5,
            width: "max-content",
          }}
        >
          {CUTOUT_TYPES.map((type) => (
            <Fragment key={type}>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ alignSelf: "center", pr: 1 }}
              >
                {CUTOUT_LABELS[type] ?? type}
              </Typography>
              {epochs.map((epoch) => (
                <Cutout
                  key={epoch.id}
                  epoch={epoch}
                  type={type}
                  zoom={zoomOf(epoch)}
                />
              ))}
            </Fragment>
          ))}
          <Box />
          {epochs.map((epoch) => (
            <Typography
              key={epoch.id}
              variant="caption"
              sx={{ wordBreak: "break-all" }}
            >
              <Link to={`/source/${epoch.id}`}>{epoch.id}</Link>
            </Typography>
          ))}
        </Box>
      </Box>
      {fieldsOfView.length > 1 && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Field of view
          </Typography>
          <SegmentedControl
            size="small"
            value={sameScale}
            onChange={setSameScale}
            options={[
              { value: false, label: "Native" },
              { value: true, label: "Same" },
            ]}
          />
        </Box>
      )}
    </Paper>
  );
};

const TrackScanner = () => {
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(25);
  const [onlyMultiEpoch, setOnlyMultiEpoch] = useState(true);
  const userGroups = useGetGroupsQuery().data?.userAccessible ?? [];

  const { data, isFetching, error } = useGetSuperObjsQuery({
    includeEpochs: true,
    isRoid: true,
    pageNumber: page + 1,
    numPerPage: perPage,
  });

  const tracks = (data?.superObjs || []).filter(
    (track) => !onlyMultiEpoch || distinctEpochs(track).length > 1,
  );
  const hiddenSingles = (data?.superObjs.length ?? 0) - tracks.length;

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1.5 }}>
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={onlyMultiEpoch}
              onChange={(e) => setOnlyMultiEpoch(e.target.checked)}
            />
          }
          label="Multi-epoch only"
        />
        {isFetching && <CircularProgress size={18} />}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Could not load tracks.
        </Alert>
      )}

      {data && tracks.length === 0 && (
        <Paper
          variant="outlined"
          sx={{
            py: 6,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 1,
          }}
        >
          <Typography color="text.secondary">No tracks to review</Typography>
          {hiddenSingles > 0 && (
            <Button size="small" onClick={() => setOnlyMultiEpoch(false)}>
              Show {hiddenSingles} single-epoch track
              {hiddenSingles === 1 ? "" : "s"}
            </Button>
          )}
        </Paper>
      )}

      <Stack spacing={2}>
        {tracks.map((track) => (
          <TrackRow key={track.id} track={track} userGroups={userGroups} />
        ))}
      </Stack>

      {((data?.totalMatches ?? 0) > perPage || page > 0) && (
        <TablePagination
          component="div"
          count={data?.totalMatches || 0}
          page={page}
          onPageChange={(_e, value) => setPage(value)}
          rowsPerPage={perPage}
          onRowsPerPageChange={(e) => {
            setPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[25, 50, 100]}
        />
      )}
    </Box>
  );
};

export default TrackScanner;
