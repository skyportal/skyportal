import { useState } from "react";
import { Link } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
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
import SaveTrackButton from "./SaveTrackButton";

/** The alert cutouts, in the order a reviewer reads them down a column. */
const CUTOUT_TYPES = ["new", "ref", "sub"] as const;
const CUTOUT_LABELS: Record<string, string> = {
  new: "Science",
  ref: "Template",
  sub: "Difference",
};

/** BOOM writes one of these on a track's earliest epoch, carrying the orbit. */
const TRACK_ANNOTATION_ORIGIN = "boom:track";

/** At or above this digest2 score the MPC treats a track as an NEO candidate. */
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

/**
 * The track's distinct detections.
 *
 * A detection may belong to more than one of a track's tracklets, and each
 * tracklet row arrives as its own Obj, so the same detection can appear several
 * times. Keyed on position rather than Obj id for that reason: the repeats are
 * one detection recorded twice, at one time and one place, and a moving object
 * does not revisit a position within a track.
 */
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

const cutoutUrl = (epoch: SuperObjEpoch, type: string) =>
  (epoch.thumbnails || []).find((t) => t.type === type)?.public_url || null;

/**
 * One epoch's column of cutouts. A reviewer judges a linkage by reading across
 * the row: a real moving object steps cleanly between epochs, while a bad
 * linkage mixes unrelated sources.
 */
const EpochColumn = ({ epoch }: { epoch: SuperObjEpoch }) => (
  <Stack spacing={0.5} sx={{ minWidth: 104 }}>
    {CUTOUT_TYPES.map((type) => {
      const url = cutoutUrl(epoch, type);
      return (
        <Box
          key={type}
          sx={{
            width: 100,
            height: 100,
            bgcolor: "action.hover",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          }}
        >
          {url ? (
            <img
              src={url}
              alt={`${CUTOUT_LABELS[type] ?? type} cutout for ${epoch.id}`}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <Typography variant="caption" color="text.secondary">
              no {(CUTOUT_LABELS[type] ?? type).toLowerCase()}
            </Typography>
          )}
        </Box>
      );
    })}
    <Typography variant="caption" noWrap sx={{ maxWidth: 100 }}>
      <Link to={`/source/${epoch.id}`}>{epoch.id}</Link>
    </Typography>
  </Stack>
);

/** One track: how it was built, then a column of cutouts per detection epoch. */
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

  const epochs = distinctEpochs(track);
  const repeats = track.objs.length - epochs.length;

  // How the track was assembled, not how good it is. Measured against labelled
  // tracks, the fit residual does not separate real linkages from merged ones:
  // the failures fell at 0.19 to 0.28 arcsec while correct tracks ran from 0.01
  // to 1.58, so a reviewer trusting a low residual would be wrong. Sky span and
  // motion regularity separate no better. The cutouts are the judgement.
  const facts: [string, string | null][] = [
    ["detections", String(epochs.length)],
    ["tracklets", num(orbit["n_tracklets"], 0)],
    ["nights", num(orbit["nights"], 0)],
    ["residual", num(orbit["fit_residual_arcsec"], 2)],
    ["r (au)", num(orbit["hypothesis_r_au"], 2)],
    ["dr/dt", num(orbit["hypothesis_rdot_au_per_day"], 4)],
    ["digest2", num(digest2, 1)],
  ];

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{ mb: 1, alignItems: "center", flexWrap: "wrap" }}
      >
        <Typography variant="subtitle1">
          {track.name || `Track ${track.id}`}
        </Typography>
        {isNeo && <Chip size="small" color="warning" label="NEO candidate" />}
        <Box sx={{ flexGrow: 1 }} />
        <SaveTrackButton
          trackName={track.name || `Track ${track.id}`}
          epochs={epochs}
          userGroups={userGroups}
        />
        {facts
          .filter(([, value]) => value !== null)
          .map(([label, value]) => (
            <Chip
              key={label}
              size="small"
              variant="outlined"
              label={`${label} ${value}`}
            />
          ))}
      </Stack>

      {repeats > 0 && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block" }}
        >
          {repeats} of this track&apos;s {track.objs.length} rows repeat a
          detection already shown: a detection can belong to more than one
          tracklet, so the annotation&apos;s epoch count is rows rather than
          distinct detections.
        </Typography>
      )}

      {Object.keys(orbit).length === 0 && (
        <Typography variant="caption" color="text.secondary">
          No {TRACK_ANNOTATION_ORIGIN} annotation on this track, so nothing is
          known about how it was built. The cutouts below are still the linkage
          to judge.
        </Typography>
      )}

      <Box sx={{ overflowX: "auto", pb: 1 }}>
        <Stack direction="row" spacing={1}>
          <Stack spacing={0.5} sx={{ justifyContent: "flex-start", pt: 0.5 }}>
            {CUTOUT_TYPES.map((type) => (
              <Box
                key={type}
                sx={{
                  height: 100,
                  display: "flex",
                  alignItems: "center",
                  pr: 1,
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  {CUTOUT_LABELS[type] ?? type}
                </Typography>
              </Box>
            ))}
          </Stack>
          {epochs.map((epoch) => (
            <EpochColumn key={epoch.id} epoch={epoch} />
          ))}
        </Stack>
      </Box>
    </Paper>
  );
};

/**
 * Review linked moving-object tracks.
 *
 * A track is a SuperObj with one Obj per detection epoch, so a reviewer needs
 * every epoch side by side rather than the scanning page's one row per
 * detection. Single-epoch moving-object SuperObjs are known bodies recorded by
 * the solar-system ingest and are filtered out here for the same reason they
 * are never submitted: the MPC already has them.
 */
const TrackScanner = () => {
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(10);
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

  return (
    <Box sx={{ p: 2 }}>
      <Stack
        direction="row"
        spacing={2}
        sx={{ mb: 2, alignItems: "center", flexWrap: "wrap" }}
      >
        <Typography variant="h5">Moving object tracks</Typography>
        <FormControlLabel
          control={
            <Switch
              checked={onlyMultiEpoch}
              onChange={(e) => setOnlyMultiEpoch(e.target.checked)}
            />
          }
          label="Multi-epoch only"
        />
        {isFetching && <CircularProgress size={20} />}
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Could not load tracks.
        </Alert>
      )}

      {!isFetching && tracks.length === 0 && (
        <Typography color="text.secondary">
          No tracks to review.
          {onlyMultiEpoch && data?.totalMatches
            ? " Every moving object on this page has a single epoch, which means a known body rather than a new track."
            : ""}
        </Typography>
      )}

      {tracks.map((track) => (
        <TrackRow key={track.id} track={track} userGroups={userGroups} />
      ))}

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
        rowsPerPageOptions={[10, 25, 50]}
      />
    </Box>
  );
};

export default TrackScanner;
