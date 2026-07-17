import React, { useEffect, useState, useMemo, Suspense } from "react";
import { useNavigate, Link } from "react-router-dom";

import Button from "@mui/material/Button";
import { makeStyles } from "tss-react/mui";
import Grid from "@mui/material/Grid";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import Tooltip from "@mui/material/Tooltip";
import Paper from "@mui/material/Paper";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";

import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";

import StyledDataGrid from "../StyledDataGrid";
import SaveAlertButton from "./SaveAlertButton";
import ThumbnailList from "../thumbnail/ThumbnailList";
import SharePage from "../SharePage";
import withRouter from "../withRouter";

import { ra_to_hours, dec_to_dms } from "../../units";

import {
  useGetAlertDataQuery,
  useGetBoomObjectQuery,
} from "../../ducks/boom_alert";
import {
  useCheckSourceMutation,
  useLazyGetSourceQuery,
} from "../../ducks/source";
import { useLazyFetchSourcesQuery } from "../../ducks/sources";
import { useGetGroupsQuery } from "../../ducks/groups";
import { bytes2image } from "../../utils/imageProcessing";

// ── Survey inference ──────────────────────────────────────────────────────────

function inferSurvey(objectId: any): string | null {
  if (!objectId) return null;
  if (objectId.toUpperCase().startsWith("ZTF")) return "ZTF";
  if (/^\d{15,}$/.test(objectId)) return "LSST";
  return null;
}

// ── Survey-agnostic field accessors ──────────────────────────────────────────

const getCandid = (alert: any) => {
  return (
    alert?.diaSourceId ??
    alert?.candid ??
    alert?.candidate?.candid ??
    alert?._id
  );
};

const getJd = (alert: any) => alert?.candidate?.jd;

const getRa = (alert: any) =>
  alert?.candidate?.ra ?? alert?.candidate?.coord_ra;
const getDec = (alert: any) =>
  alert?.candidate?.dec ?? alert?.candidate?.coord_dec;

// ── Row builder ───────────────────────────────────────────────────────────────

const buildRow = (alert: any, survey: string | null) => ({
  candid: getCandid(alert),
  jd: getJd(alert),
  band: alert?.candidate?.band,
  magpsf: alert?.candidate?.magpsf,
  sigmapsf: alert?.candidate?.sigmapsf,
  isdiffpos: alert?.candidate?.isdiffpos,
  drb: survey === "ZTF" ? alert?.candidate?.drb : alert?.candidate?.reliability,
  snr: alert?.candidate?.snr_psf ?? alert?.candidate?.snr,
  ...(survey === "ZTF" ? { programid: alert?.candidate?.programid } : {}),
});

// ── Column definitions ────────────────────────────────────────────────────────

const fmt = (decimals: number) => (params: any) =>
  params.value != null ? params.value.toFixed(decimals) : "—";

const buildColumns = (survey: string | null): any[] => {
  const isLSST = survey === "LSST";

  const columns: any[] = [
    {
      field: "candid",
      headerName: isLSST ? "diaSourceId" : "candid",
      flex: 1,
      minWidth: 120,
      filterable: false,
      sortable: true,
      sortingOrder: ["desc", "asc"],
    },
    {
      field: "jd",
      headerName: isLSST ? "MJD" : "JD",
      flex: 1,
      minWidth: 100,
      filterable: false,
      sortable: true,
      sortingOrder: ["desc", "asc"],
      renderCell: fmt(5),
    },
    {
      field: "band",
      headerName: "band",
      flex: 1,
      minWidth: 80,
      filterable: true,
      sortable: true,
    },
    {
      field: "magpsf",
      headerName: "magpsf",
      flex: 1,
      minWidth: 90,
      filterable: false,
      sortable: true,
      renderCell: fmt(3),
    },
    {
      field: "sigmapsf",
      headerName: "sigmapsf",
      flex: 1,
      minWidth: 90,
      filterable: false,
      sortable: true,
      renderCell: fmt(3),
    },
    {
      field: "isdiffpos",
      headerName: "isdiffpos",
      flex: 1,
      minWidth: 90,
      filterable: true,
      sortable: true,
      renderCell: (params: any) =>
        params.value != null ? String(params.value) : "—",
    },
    {
      field: "drb",
      headerName: isLSST ? "reliability" : "drb",
      flex: 1,
      minWidth: 100,
      filterable: false,
      sortable: true,
      sortingOrder: ["desc", "asc"],
      renderCell: fmt(5),
    },
    {
      field: "snr",
      headerName: "snr",
      flex: 1,
      minWidth: 80,
      filterable: false,
      sortable: true,
      renderCell: fmt(2),
    },
  ];

  if (survey === "ZTF") {
    columns.push({
      field: "programid",
      headerName: "programid",
      flex: 1,
      minWidth: 100,
      filterable: true,
      sortable: true,
    });
  }

  return columns;
};

// ── Photometry plot ───────────────────────────────────────────────────────────

const VegaPlotAlert = React.lazy(() => import("../plot/VegaPlotAlert"));

interface AlertPhotometryPlotProps {
  objectId: string;
  jd?: number | null;
  survey: string;
}

const AlertPhotometryPlot = ({
  objectId,
  jd = null,
  survey,
}: AlertPhotometryPlotProps) => {
  const { data: objectData } = useGetBoomObjectQuery(
    { survey, id: objectId },
    { skip: !survey },
  );
  const [showUpperLimits, setShowUpperLimits] = useState(true);
  const [showForcedPhotometry, setShowForcedPhotometry] = useState(true);
  const [forcedPhotometrySNR, setForcedPhotometrySNR] = useState<any>(3);

  if (!objectData || jd === null) {
    return <div>Loading photometry...</div>;
  }

  let photometry: any[] = [];
  if (typeof objectData === "object") {
    const detections = (objectData.prv_candidates || []).map((d: any) => ({
      ...d,
      origin: "alert",
    }));
    const nonDetections = (objectData.prv_nondetections || []).map(
      (d: any) => ({
        ...d,
        magpsf: null,
        sigmapsf: null,
        origin: "alert",
      }),
    );
    photometry = detections.concat(nonDetections);

    const fp_hists = showForcedPhotometry
      ? (objectData.fp_hists || []).map((d: any) => {
          const point: any = { ...d, origin: "fp" };
          if (d.snr_psf > forcedPhotometrySNR) {
            point.magpsf = d.magpsf;
            point.sigmapsf = d.sigmapsf;
          } else {
            point.magpsf = null;
            point.sigmapsf = null;
            if (d.magpsf) point.diffmaglim = d.magpsf;
          }
          return point;
        })
      : [];

    photometry = photometry.concat(fp_hists);
    if (!showUpperLimits) {
      photometry = photometry.filter((d: any) => d.magpsf);
    }
  }

  if (photometry.length === 0) {
    return <div>No photometry found</div>;
  }

  return (
    <div style={{ width: "100%", height: "90%" }}>
      <VegaPlotAlert values={photometry} jd={jd} />
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "flex-start",
          gap: "0.5rem",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
          }}
        >
          <Switch
            checked={showUpperLimits}
            onChange={() => setShowUpperLimits((v) => !v)}
            name="showUpperLimits"
            slotProps={{ input: { "aria-label": "show upper limits" } }}
          />
          <div>Upper limits</div>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
          }}
        >
          <Switch
            checked={showForcedPhotometry}
            onChange={() => setShowForcedPhotometry((v) => !v)}
            name="showForcedPhotometry"
            slotProps={{ input: { "aria-label": "show forced photometry" } }}
          />
          <div>Forced photometry</div>
        </div>
        <TextField
          label="SNR Threshold (FP only)"
          type="number"
          value={forcedPhotometrySNR}
          size="small"
          onChange={(e) => setForcedPhotometrySNR(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
      </div>
    </div>
  );
};

// ── Cross-matches panel ───────────────────────────────────────────────────────

const PRIORITY_COLS = ["_id", "coordinates.distance_arcsec", "ra", "dec"];

const flattenEntry = (entry: any) => {
  const flat: any = {};
  Object.entries(entry).forEach(([k, v]) => {
    if (v !== null && typeof v === "object" && !Array.isArray(v)) {
      Object.entries(v).forEach(([sk, sv]) => {
        flat[`${k}.${sk}`] = sv;
      });
    } else {
      flat[k] = v;
    }
  });
  return flat;
};

const fmtCell = (v: any) => {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return JSON.stringify(v);
  if (typeof v === "object") return JSON.stringify(v);
  if (typeof v === "number" && !Number.isInteger(v)) return v.toFixed(5);
  return String(v);
};

interface CatalogTableProps {
  entries: any[];
}

const CatalogTable = ({ entries }: CatalogTableProps) => {
  const flat = entries.map(flattenEntry);
  const allKeys = Array.from(new Set(flat.flatMap((e: any) => Object.keys(e))));
  const priority = PRIORITY_COLS.filter((c) => allKeys.includes(c));
  const rest = allKeys.filter((c) => !PRIORITY_COLS.includes(c)).sort();
  const columns = [...priority, ...rest];

  const cellSx = { padding: "2px 8px", whiteSpace: "nowrap" };
  return (
    <TableContainer style={{ overflowX: "auto" }}>
      <Table size="small" style={{ fontSize: "0.8rem" }}>
        <TableHead>
          <TableRow>
            {columns.map((col) => (
              <TableCell key={col} sx={{ ...cellSx, fontWeight: 600 }}>
                {col === "coordinates.distance_arcsec" ? `dist (")` : col}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {flat.map((row: any, i: number) => (
            <TableRow key={i} hover>
              {columns.map((col) => (
                <TableCell key={col} sx={cellSx}>
                  {fmtCell(row[col])}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

interface CrossMatchesPanelProps {
  cross_matches: Record<string, any>;
}

const CrossMatchesPanel = ({ cross_matches }: CrossMatchesPanelProps) => {
  const allCatalogs = Object.keys(cross_matches).sort();
  const withMatches = allCatalogs.filter(
    (k) => Array.isArray(cross_matches[k]) && cross_matches[k].length > 0,
  );
  const withoutMatches = allCatalogs.filter(
    (k) => !Array.isArray(cross_matches[k]) || cross_matches[k].length === 0,
  );

  if (allCatalogs.length === 0) {
    return (
      <Typography variant="body2" style={{ padding: "0.5rem" }}>
        No cross-matches found.
      </Typography>
    );
  }

  const catalogAccordion = (catalog: string, hasMatches: boolean) => {
    const entries = cross_matches[catalog];
    const count = hasMatches ? entries.length : 0;
    return (
      <Accordion
        key={catalog}
        disableGutters
        disabled={!hasMatches}
        defaultExpanded={false}
        sx={{
          mb: "0.375rem",
          "&.Mui-disabled": { backgroundColor: "transparent", opacity: 1 },
          "&:before": { display: "none" },
        }}
      >
        <AccordionSummary
          expandIcon={hasMatches ? <ExpandMoreIcon /> : null}
          style={{ cursor: hasMatches ? "pointer" : "default" }}
        >
          <Typography
            style={{
              fontWeight: 500,
              color: hasMatches ? "inherit" : "text.disabled",
              opacity: hasMatches ? 1 : 0.45,
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
            }}
          >
            {catalog}
            <Chip
              size="small"
              label={count}
              color={hasMatches ? "default" : "default"}
              style={{ opacity: hasMatches ? 1 : 0.45 }}
            />
          </Typography>
        </AccordionSummary>
        {hasMatches && (
          <AccordionDetails style={{ padding: "0 0 0.5rem 0" }}>
            <CatalogTable entries={entries} />
          </AccordionDetails>
        )}
      </Accordion>
    );
  };

  const allOrdered = [...withMatches, ...withoutMatches];
  return (
    <div>
      {allOrdered.map((catalog) =>
        catalogAccordion(catalog, withMatches.includes(catalog)),
      )}
    </div>
  );
};

// ── Styles ────────────────────────────────────────────────────────────────────

const useStyles = makeStyles()((theme) => ({
  root: { width: "100%" },
  itemPadding: { padding: "0.5rem 0 0.5rem 0" },
  saveAlertButton: { margin: "0.5rem 0 0 0", paddingTop: "0.5rem" },
  header: { paddingBottom: "0.625rem", color: theme.palette.text.primary },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  accordionDetails: { width: "100%" },
  name: {
    fontSize: "200%",
    fontWeight: "900",
    color: "darkgray",
    display: "inline-block",
  },
  alignRight: { display: "inline-block", verticalAlign: "super" },
  sourceInfo: { display: "flex", flexFlow: "row wrap", alignItems: "center" },
  position: { fontWeight: "bold", fontSize: "110%" },
}));

function isString(x: any) {
  return Object.prototype.toString.call(x) === "[object String]";
}

// ── Main component ────────────────────────────────────────────────────────────

interface AlertProps {
  route: any;
}

const Font: any = "font";

const Alert = ({ route }: AlertProps) => {
  const objectId = route.id;
  const survey = inferSurvey(objectId);

  const navigate = useNavigate();
  const { classes } = useStyles();
  const [savedSource, setSavedSource] = useState(false);
  const [fetchedDuplicates, setFetchedDuplicates] = useState(false);

  const [triggerCheckSource] = useCheckSourceMutation();
  const [triggerGetSource, getSourceResult] = useLazyGetSourceQuery();
  const [triggerFetchSources, fetchSourcesResult] = useLazyFetchSourcesQuery();

  // RTK Query: read results from the query hooks (no more redux slices).
  const sources: any = fetchSourcesResult.data;
  const source: any = getSourceResult.data;
  const loadedSourceId = getSourceResult.data?.id;
  const userAccessibleGroups = useGetGroupsQuery().data?.userAccessible ?? [];
  const userAccessibleGroupIds = useMemo(
    () => userAccessibleGroups?.map((a: any) => a.id),
    [userAccessibleGroups],
  );

  const [candid, setCandid] = useState<any>(null);
  const [jd, setJd] = useState<any>(null);
  const [cutoutDataUris, setCutoutDataUris] = useState<any>(null);

  useEffect(() => {
    if (!objectId || !survey) return;
    setCutoutDataUris(null);
    fetch(
      `/api/boom/surveys/${survey}/alerts/cutouts?objectId=${objectId}&which=brightest&file_format=fits`,
      { credentials: "include" },
    )
      .then((r) => r.json())
      .then((json) => {
        if (json.status !== "success" || !json.data) {
          setCutoutDataUris({});
          return;
        }
        const d = json.data;
        setCutoutDataUris({
          new: bytes2image(d.cutoutScience, survey, "science", "bone") ?? null,
          ref:
            bytes2image(d.cutoutTemplate, survey, "template", "bone") ?? null,
          sub:
            bytes2image(d.cutoutDifference, survey, "difference", "bone") ??
            null,
        });
      })
      .catch(() => setCutoutDataUris({}));
  }, [objectId, survey]);

  const [panelXMatchExpanded, setPanelXMatchExpanded] = useState(true);
  const handlePanelXMatchChange =
    (panel: any) => (_: any, isExpanded: boolean) =>
      setPanelXMatchExpanded(isExpanded ? panel : false);

  const { data: alertData, isError: alertError } = useGetAlertDataQuery(
    { survey: survey as string, id: objectId },
    { skip: !survey },
  );
  const { data: objectData, isError: objectError } = useGetBoomObjectQuery(
    { survey: survey as string, id: objectId },
    { skip: !survey },
  );

  // ── Source existence check ──────────────────────────────────────────────────
  useEffect(() => {
    const fetchExistingSource = async () => {
      const result = await triggerCheckSource({
        id: objectId,
        params: { nameOnly: true },
      });
      if (
        result.data?.status === "success" &&
        result.data?.data?.source_exists === true
      ) {
        setSavedSource(true);
        triggerGetSource(objectId);
      } else {
        setSavedSource(false);
      }
    };
    if (objectId !== loadedSourceId) {
      fetchExistingSource();
    }
  }, [objectId]);

  // ── Alert data → default candid/jd + duplicate check ────────────────────────
  // getAlertData/getBoomObject are fetched by the query hooks above; derive the
  // default candid/jd (and the duplicate check) once the alerts arrive.
  useEffect(() => {
    if (!Array.isArray(alertData) || alertData.length === 0) return;

    const candids = Array.from(new Set(alertData.map((a: any) => getCandid(a))))
      .filter((c: any) => c != null)
      .sort();
    const jds = Array.from(new Set(alertData.map((a: any) => getJd(a))))
      .filter((j: any) => j != null)
      .sort();

    if (candids.length === 0) return;
    setCandid(candids[candids.length - 1]);
    setJd(jds[jds.length - 1]);

    const lastAlert = alertData.find(
      (a: any) => getCandid(a) === candids[candids.length - 1],
    );
    const ra = getRa(lastAlert);
    const dec = getDec(lastAlert);
    if (ra != null && dec != null) {
      triggerFetchSources({ ra, dec, radius: 2 / 3600 }).then((result: any) => {
        if (result.data?.["status"] === "success") setFetchedDuplicates(true);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alertData]);

  // ── Unknown survey guard ────────────────────────────────────────────────────
  if (!survey) {
    return (
      <div style={{ padding: "1rem" }}>
        <Typography variant="h5" className={classes.header}>
          Unknown object format: <b>{objectId}</b>
        </Typography>
        <Typography variant="body1">
          Could not determine the survey from this object ID. Expected a ZTF
          name (e.g. ZTF21abc...) or an LSST diaObjectId (15+ digit integer).
        </Typography>
      </div>
    );
  }

  // ── Alert candidate lookup helpers ─────────────────────────────────────────
  const alertsForObject = Array.isArray(alertData) ? alertData : [];

  const currentAlert = alertsForObject.find(
    (a: any) => getCandid(a) === candid,
  );

  const rows = alertsForObject.map((a: any) => buildRow(a, survey));
  const columns = buildColumns(survey);

  let cross_matches: Record<string, any> = {};
  if (objectData && !isString(objectData)) {
    cross_matches = objectData?.cross_matches ?? {};
  }

  const thumbnails = cutoutDataUris
    ? [
        { type: "new", id: 0, public_url: cutoutDataUris.new },
        { type: "ref", id: 1, public_url: cutoutDataUris.ref },
        { type: "sub", id: 2, public_url: cutoutDataUris.sub },
      ]
    : [];

  // ── Loading / error states ─────────────────────────────────────────────────
  if (alertData == null && !alertError) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  if (alertError || objectError) {
    return <div>Failed to fetch alert data, please try again later.</div>;
  }
  if (alertData?.length === 0) {
    return (
      <Typography variant="h5" className={classes.header}>
        {objectId} not found
      </Typography>
    );
  }

  if (!alertData?.length) {
    return null;
  }

  return (
    <Grid container spacing={2}>
      {/* ── Header card ─────────────────────────────────────────────────── */}
      <Grid size={12}>
        <Paper>
          <Grid container spacing={0} style={{ paddingBottom: "1rem" }}>
            {/* Left: metadata, save button */}
            <Grid size={{ xs: 12, lg: 6 }}>
              <div
                style={{
                  padding: "0.5rem 1rem 0 1rem",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <div>
                  <div className={classes.alignRight}>
                    <SharePage />
                  </div>
                  <div className={classes.name}>{objectId}</div>
                  {objectData?.missing === true && (
                    <Chip
                      title="Aux data for this object is temporarily unavailable. Detections were fetched using individual alerts instead."
                      size="small"
                      label="Warning: missing aux data"
                      style={{ backgroundColor: "#E9D502" }}
                      icon={<WarningAmberIcon />}
                    />
                  )}
                </div>

                {candid !== null && currentAlert && (
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <div>
                      <b>{survey === "LSST" ? "diaSourceId" : "candid"}:</b>
                      &nbsp;{candid}
                    </div>
                    <div className={classes.sourceInfo}>
                      <b>Position (J2000):&nbsp;&nbsp;</b>
                      <span className={classes.position}>
                        {ra_to_hours(getRa(currentAlert), ":")}
                        &nbsp;
                        {dec_to_dms(getDec(currentAlert), ":")}
                        &nbsp;
                      </span>
                    </div>
                    <div className={classes.sourceInfo}>
                      <div>
                        (&alpha;,&delta;= {getRa(currentAlert)}, &nbsp;
                        {getDec(currentAlert)}
                        {currentAlert?.coordinates?.b != null && (
                          <>
                            ;&nbsp; l,b=
                            {currentAlert.coordinates?.l?.toFixed(6)}, &nbsp;
                            {currentAlert.coordinates?.b?.toFixed(6)}
                          </>
                        )}
                        )
                      </div>
                    </div>
                  </div>
                )}

                {savedSource || loadedSourceId === objectId ? (
                  <div>
                    <div className={classes.itemPadding}>
                      <Chip
                        size="small"
                        label="Previously Saved"
                        clickable
                        onClick={() => navigate(`/source/${objectId}`)}
                        onDelete={() =>
                          window.open(`/source/${objectId}`, "_blank")
                        }
                        deleteIcon={<OpenInNewIcon />}
                        color="primary"
                      />
                    </div>
                    {source?.id === objectId &&
                      source.groups?.map((group: any) => (
                        <Tooltip
                          key={group.id}
                          title={`Saved at ${group.saved_at} by ${group.saved_by?.username}`}
                        >
                          <Chip
                            label={
                              group.nickname
                                ? group.nickname.substring(0, 15)
                                : group.name.substring(0, 15)
                            }
                            size="small"
                            data-testid={`groupChip_${group.id}`}
                          />
                        </Tooltip>
                      ))}
                    <div className={classes.itemPadding}>
                      <div className={classes.saveAlertButton}>
                        <SaveAlertButton
                          alert={{
                            id: objectId,
                            survey,
                            candid,
                            group_ids: userAccessibleGroupIds,
                          }}
                          userGroups={userAccessibleGroups}
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className={classes.itemPadding}>
                    <Chip size="small" label="NOT SAVED" />
                    <br />
                    <div className={classes.saveAlertButton}>
                      <SaveAlertButton
                        alert={{
                          id: objectId,
                          survey,
                          candid,
                          group_ids: userAccessibleGroupIds,
                        }}
                        userGroups={userAccessibleGroups}
                      />
                    </div>
                  </div>
                )}

                {fetchedDuplicates &&
                  sources?.sources?.length > 0 &&
                  !(
                    sources.sources.length === 1 &&
                    sources.sources[0].id === objectId
                  ) && (
                    <div className={classes.sourceInfo}>
                      <b>
                        <Font color="#457b9d">Possible duplicate of:</Font>
                      </b>
                      &nbsp;
                      {sources.sources.map(
                        (dup: any) =>
                          dup?.id !== objectId && (
                            <Link
                              key={dup.id}
                              to={`/source/${dup.id}`}
                              role="link"
                            >
                              <Button size="small">{dup.id}</Button>
                            </Link>
                          ),
                      )}
                    </div>
                  )}
              </div>
            </Grid>

            {/* Right: thumbnails + cutout save panel */}
            <Grid size={{ xs: 12, lg: 6 }}>
              {candid !== null && (
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr",
                    gap: "0.5rem",
                    gridAutoFlow: "row",
                    padding: "1rem 1rem 0 1rem",
                  }}
                >
                  {cutoutDataUris === null ? (
                    <CircularProgress size={32} style={{ margin: "auto" }} />
                  ) : (
                    <ThumbnailList
                      ra={getRa(currentAlert)}
                      dec={getDec(currentAlert)}
                      thumbnails={thumbnails}
                      displayTypes={["new", "ref", "sub"]}
                      useGrid={false}
                      noMargin
                      size="100%"
                      minSize="5rem"
                      maxSize="24vh"
                    />
                  )}
                </div>
              )}
            </Grid>
          </Grid>
        </Paper>
      </Grid>

      {/* ── Photometry plot ──────────────────────────────────────────────── */}
      <Grid size={12}>
        <Suspense fallback={<CircularProgress color="secondary" />}>
          <Paper
            style={{
              width: "100%",
              height: "55vh",
              padding: "1rem 0.5rem 0.5rem 0.5rem",
              backgroundColor: "white",
            }}
          >
            <AlertPhotometryPlot objectId={objectId} jd={jd} survey={survey} />
          </Paper>
        </Suspense>
      </Grid>

      {/* ── Alert history table ──────────────────────────────────────────── */}
      <Grid size={12}>
        <Paper elevation={1}>
          <Typography variant="h6" style={{ padding: "0.5rem" }}>
            Alerts
          </Typography>
          <StyledDataGrid
            autoHeight
            title="Alerts"
            rows={rows}
            columns={columns}
            getRowId={(row: any) => row.candid}
            initialState={{
              sorting: { sortModel: [{ field: "jd", sort: "desc" }] },
            }}
            pageSizeOptions={[10, 25, 50, 100]}
          />
        </Paper>
      </Grid>

      {/* ── Cross-matches ────────────────────────────────────────────────── */}
      <Grid size={12}>
        <Accordion
          expanded={panelXMatchExpanded}
          onChange={handlePanelXMatchChange(true)}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="panel-content"
            id="xmatch-panel-header"
          >
            <Typography className={classes.accordionHeading}>
              Cross-matches
            </Typography>
          </AccordionSummary>
          <AccordionDetails className={classes.accordionDetails}>
            <CrossMatchesPanel cross_matches={cross_matches} />
          </AccordionDetails>
        </Accordion>
      </Grid>
    </Grid>
  );
};

export default withRouter(Alert);
