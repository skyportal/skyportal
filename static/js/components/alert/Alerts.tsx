import { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";

import Card from "@mui/material/Card";
import CardActions from "@mui/material/CardActions";
import CardContent from "@mui/material/CardContent";

import TextField from "@mui/material/TextField";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormHelperText from "@mui/material/FormHelperText";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import SaveIcon from "@mui/icons-material/Save";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";

import Grid from "@mui/material/Grid";

import { makeStyles } from "tss-react/mui";
import { useForm, Controller } from "react-hook-form";
import Paper from "@mui/material/Paper";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";

import StyledDataGrid from "../StyledDataGrid";

import Button from "../Button";
import ThumbnailList from "../thumbnail/ThumbnailList";
import FormValidationError from "../FormValidationError";

import { dms_to_dec, hours_to_ra } from "../../units";
import { greatCircleDistance } from "../../utils";

import { useSaveAlertAsSourceMutation } from "../../ducks/boom_alert";
import { useLazyGetAlertsQuery } from "../../ducks/boom_alerts";
import { useGetGroupsQuery } from "../../ducks/groups";
import { bytes2image } from "../../utils/imageProcessing";

function isString(x: any) {
  return Object.prototype.toString.call(x) === "[object String]";
}

function inferSurvey(objectId: any): string | null {
  if (!objectId) return null;
  if (objectId.toUpperCase().startsWith("ZTF")) return "ZTF";
  // WINTER objectIds are WNTR-prefixed (e.g. WNTR26capcd); BOOM knows the
  // survey as WINTER, so bridge the two namespaces here.
  if (objectId.toUpperCase().startsWith("WNTR")) return "WINTER";
  if (/^\d{15,}$/.test(objectId)) return "LSST";
  return null;
}

const useStyles = makeStyles()((theme) => ({
  root: {
    margin: 0,
    padding: 0,
    width: "100%",
    "& > *": {
      margin: 0,
      padding: 0,
    },
  },
  cardContent: {
    padding: "0.75rem",
    paddingBottom: 0,
  },
  cardActions: {
    padding: "0.75rem",
  },
  whitish: {
    color: "#f0f0f0",
  },
  visuallyHidden: {
    border: 0,
    clip: "rect(0 0 0 0)",
    height: 1,
    margin: -1,
    overflow: "hidden",
    padding: 0,
    position: "absolute",
    top: 20,
    width: 1,
  },
  search_button: {
    color: "#f0f0f0 !important",
  },
  margin_bottom: {
    "margin-bottom": "2em",
  },
  margin_left: {
    "margin-left": "2em",
  },
  image: {
    padding: theme.spacing(1),
    textAlign: "center",
    color: theme.palette.text.secondary,
  },
  paper: {
    padding: theme.spacing(2),
    textAlign: "center",
    color: theme.palette.text.secondary,
  },
  formControl: {
    width: "100%",
  },
  selectEmpty: {
    width: "100%",
  },
  header: {
    paddingBottom: "0.625rem",
  },
  button: {
    textTransform: "none",
  },
  wrapperRoot: {
    display: "flex",
    alignItems: "center",
  },
  wrapper: {
    margin: 0,
    position: "relative",
  },
  buttonProgress: {
    color: theme.palette.text.secondary,
    position: "absolute",
    top: "50%",
    left: "50%",
    marginTop: -12,
    marginLeft: -12,
  },
  grid_item_table: {
    order: 2,
    [theme.breakpoints.up("lg")]: {
      order: 1,
    },
  },
  grid_item_search_box: {
    order: 1,
    [theme.breakpoints.up("lg")]: {
      order: 2,
    },
  },
  marginTop: {
    marginTop: "1em",
  },
}));

interface CutoutTripletProps {
  rowObj: any;
  survey: string;
}

const CutoutTriplet = ({ rowObj, survey }: CutoutTripletProps) => {
  const [dataUris, setDataUris] = useState<any>(null);

  useEffect(() => {
    const query = rowObj.candid
      ? `candid=${rowObj.candid}`
      : `objectId=${rowObj.objectId}&which=last`;
    fetch(
      `/api/boom/surveys/${survey}/alerts/cutouts?${query}&file_format=fits`,
      {
        credentials: "include",
      },
    )
      .then((r) => r.json())
      .then((json) => {
        if (json.status !== "success" || !json.data) {
          setDataUris({});
          return;
        }
        const d = json.data;
        setDataUris({
          new: bytes2image(d.cutoutScience, survey, "science", "bone") ?? null,
          ref:
            bytes2image(d.cutoutTemplate, survey, "template", "bone") ?? null,
          sub:
            bytes2image(d.cutoutDifference, survey, "difference", "bone") ??
            null,
        });
      })
      .catch(() => setDataUris({}));
  }, [rowObj.candid, rowObj.objectId, survey]);

  return dataUris === null ? (
    <CircularProgress size={32} />
  ) : (
    <ThumbnailList
      thumbnails={[
        { type: "new", id: 0, public_url: dataUris.new },
        { type: "ref", id: 1, public_url: dataUris.ref },
        { type: "sub", id: 2, public_url: dataUris.sub },
      ]}
      ra={rowObj.ra}
      dec={rowObj.dec}
      displayTypes={["new", "ref", "sub"]}
    />
  );
};

const Alerts = () => {
  const dispatch = useAppDispatch();
  const { classes } = useStyles();

  const [searchParams] = useSearchParams();

  const { register, handleSubmit, control, getValues, reset, setValue } =
    useForm();

  const [
    triggerGetAlerts,
    { data: alerts = null, isFetching: queryInProgress },
  ] = useLazyGetAlertsQuery();
  const [saveAlertAsSource] = useSaveAlertAsSourceMutation();
  // RTK Query: groups come from the query hook (no more redux slice).
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];

  // save alerts to SP in bulk (by objectID)
  const [selectedSurvey, setSelectedSurvey] = useState("ZTF");

  const [groupByObj, setGroupByObj] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [rowsToSave, setRowsToSave] = useState<any[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  // Object IDs of the rows currently selected via the DataGrid checkboxes.
  const [selectedRowIds, setSelectedRowIds] = useState<any[]>([]);
  // candids of the rows whose cutout-triplet pull-out panel is expanded.
  const [openedRows, setOpenedRows] = useState<any[]>([]);

  useEffect(() => {
    const objectId = searchParams.get("objectId");
    const ra = parseFloat(searchParams.get("ra") as any);
    const dec = parseFloat(searchParams.get("dec") as any);
    let radius = parseFloat(searchParams.get("radius") as any);
    let radius_unit = searchParams.get("radius_unit");
    const group_by = searchParams.get("group_by_obj");
    const surveyParam = searchParams.get("survey");

    if (!objectId && (Number.isNaN(ra) || Number.isNaN(dec))) {
      return;
    }

    // Explicit survey param takes priority; infer from objectId as fallback
    const inferredSurvey = inferSurvey(objectId);
    const survey = surveyParam?.toUpperCase() || inferredSurvey || "ZTF";
    setSelectedSurvey(survey);

    // Use objectId search only when the objectId belongs to the target survey
    const objectIdMatchesSurvey = !inferredSurvey || inferredSurvey === survey;

    if (objectId && objectIdMatchesSurvey) {
      triggerGetAlerts({ survey, object_id: objectId } as any);
      reset({ object_id: objectId, instrument: survey.toLowerCase() });
    } else if (!Number.isNaN(ra) && !Number.isNaN(dec)) {
      if (!["arcsec", "arcmin", "deg", "rad"].includes(radius_unit as any)) {
        radius_unit = "arcsec";
      }
      if (Number.isNaN(radius)) {
        radius = 3.0;
      }
      triggerGetAlerts({
        survey,
        ra,
        dec,
        radius,
        radius_unit,
      } as any);
      reset({ ra, dec, radius, radius_unit, instrument: survey.toLowerCase() });
    }

    if ([true, "true", "t", "1", 1].includes(group_by as any)) {
      setGroupByObj(true);
    }
  }, [dispatch, searchParams]);

  const makeRow = (alert: any, survey: string | null) => {
    const isLSST = survey === "LSST";
    const isZTF = survey === "ZTF";
    return {
      objectId: alert?.objectId,
      candid: isLSST
        ? (alert?.diaSourceId ?? alert?.candid ?? alert?._id)
        : (alert?.candid ?? alert?.candidate?.candid ?? alert?._id),
      jd: alert?.candidate?.jd,
      ra: alert?.candidate?.ra ?? alert?.candidate?.coord_ra,
      dec: alert?.candidate?.dec ?? alert?.candidate?.coord_dec,
      band: alert?.candidate?.band,
      magpsf: alert?.candidate?.magpsf,
      sigmapsf: alert?.candidate?.sigmapsf,
      isdiffpos: alert?.candidate?.isdiffpos,
      // Real/bogus-style score: ZTF drb, LSST reliability, WINTER scorr.
      drb: isLSST
        ? alert?.candidate?.reliability
        : isZTF
          ? alert?.candidate?.drb
          : alert?.candidate?.scorr,
      snr: alert?.candidate?.snr_psf,
      ...(isLSST ? {} : { programid: alert?.candidate?.programid }),
      // ACAI/BTSbot are ZTF-specific classifiers; other surveys (e.g. WINTER)
      // don't carry them.
      ...(isZTF
        ? {
            acai_h: alert?.classifications?.acai_h,
            acai_n: alert?.classifications?.acai_n,
            acai_o: alert?.classifications?.acai_o,
            acai_v: alert?.classifications?.acai_v,
            acai_b: alert?.classifications?.acai_b,
            btsbot: alert?.classifications?.btsbot,
          }
        : {}),
    };
  };

  // Infer the survey from what's actually loaded rather than the form state,
  // so changing the instrument dropdown doesn't corrupt the existing results.
  const dataSurvey =
    (alerts?.length > 0 && inferSurvey(alerts[0]?.objectId)) || selectedSurvey;

  let rows: any[] = [];

  if (alerts !== null && !isString(alerts) && Array.isArray(alerts)) {
    rows = alerts.map((a: any) => makeRow(a, dataSurvey));
  }

  if (groupByObj === true && rows.length > 0) {
    // first find the unique objectIds
    const uniqueObjectIds = Array.from(
      new Set(rows.map((row: any) => row.objectId)),
    );
    // then build the new rows, which only contain the latest alert for each objectId
    // (highest jd)
    rows = uniqueObjectIds.map((objectId) => {
      const alertsForObject = rows.filter(
        (row: any) => row.objectId === objectId,
      );
      const latestAlert = alertsForObject.reduce((a: any, b: any) =>
        a.jd > b.jd ? a : b,
      );
      return latestAlert;
    });
    // add the separation between the ra and dec used in the form
    rows = rows.map((row: any) => {
      const { ra, dec } = getValues();
      const separation = greatCircleDistance(ra, dec, row.ra, row.dec);
      return { ...row, separation };
    });
  }

  const handleSaveDialogClose = () => {
    if (!saving) {
      setRowsToSave([]);
      setSaveDialogOpen(false);
    }
  };

  const handleSaveDialogOpen = async (objectIds: any[]) => {
    setRowsToSave(objectIds);
    setSaveDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    const { instrument } = getValues();
    const survey = (instrument || "ztf").toUpperCase();
    const objectIds = rowsToSave;
    objectIds.forEach((objectId: any) => {
      const payload = {
        group_ids: selectedGroups,
      };
      saveAlertAsSource({ survey, id: objectId, payload })
        .unwrap()
        .then(() => {
          dispatch(
            showNotification(
              `Saved ${objectId} to groups ${selectedGroups.join(", ")}`,
            ),
          );
        })
        .catch(() => {
          dispatch(
            showNotification(
              `Failed to save ${objectId} to groups ${selectedGroups.join(
                ", ",
              )}`,
              "error",
            ),
          );
        });
    });
    setSaving(false);
    setSaveDialogOpen(false);
  };

  // DataGrid row id: the candid uniquely identifies an alert (and, in grouped
  // mode, the single latest alert per objectId). Synthetic detail rows append
  // "__detail" to their parent's candid.
  const getRowId = (row: any) =>
    row.__detail ? `${row.candid}__detail` : row.candid;

  const toggleExpand = (candid: any) =>
    setOpenedRows((prev) =>
      prev.includes(candid)
        ? prev.filter((c: any) => c !== candid)
        : [...prev, candid],
    );

  // Map each selectable row id (candid) to its objectId so the bulk-save action
  // can recover the object ids from the selection model.
  const objectIdByRowId: Record<string, any> = {};
  rows.forEach((row: any) => {
    objectIdByRowId[row.candid] = row.objectId;
  });

  const isLSST = dataSurvey === "LSST";
  const isZTF = dataSurvey === "ZTF";

  const compactHeaderClass = "alerts-compact-cell";

  const expandColumn: any = {
    field: "__expand",
    headerName: "",
    width: 56,
    sortable: false,
    filterable: false,
    hideable: false,
    disableColumnMenu: true,
    // For a synthetic detail row, span the full width of the grid; otherwise a
    // single cell holding the expand toggle.
    colSpan: (_value: any, row: any) => (row.__detail ? 100 : 1),
    renderCell: (params: any) => {
      if (params.row.__detail) {
        const rowObj = params.row.__source;
        return (
          <Grid
            container
            direction="row"
            spacing={3}
            sx={{ justifyContent: "center", alignItems: "center" }}
            data-testid={`alertRow_${rowObj.candid}`}
          >
            <Grid>
              <CutoutTriplet
                rowObj={rowObj}
                survey={inferSurvey(rowObj.objectId) || dataSurvey}
              />
            </Grid>
          </Grid>
        );
      }
      const expanded = openedRows.includes(params.row.candid);
      return (
        <IconButton
          id="expandable-button"
          size="small"
          aria-label="expand row"
          onClick={() => toggleExpand(params.row.candid)}
        >
          {expanded ? <KeyboardArrowDownIcon /> : <KeyboardArrowRightIcon />}
        </IconButton>
      );
    },
  };

  const objectIdColumn: any = {
    field: "objectId",
    headerName: "Object ID",
    flex: 1,
    minWidth: 130,
    sortingOrder: ["desc", "asc", null],
    renderCell: (params: any) => {
      const value = params.value;
      return (
        <Link
          to={`/alerts/${(
            inferSurvey(value) || dataSurvey
          ).toLowerCase()}/${value}`}
          target="_blank"
          data-testid={value}
          rel="noreferrer"
        >
          <Button className={classes.button} size="small" variant="contained">
            {value}
          </Button>
        </Link>
      );
    },
  };

  const candidColumn: any = {
    field: "candid",
    headerName: dataSurvey === "LSST" ? "diaSourceId" : "candid",
    flex: 1,
    minWidth: 120,
    filterable: false,
  };

  const positionColumns: any[] = [
    {
      field: "ra",
      headerName: "R.A.",
      flex: 1,
      minWidth: 100,
      filterable: false,
      renderCell: (params: any) => params.value?.toFixed(5),
    },
    {
      field: "dec",
      headerName: "Decl.",
      flex: 1,
      minWidth: 100,
      filterable: false,
      renderCell: (params: any) => params.value?.toFixed(6),
    },
  ];

  const separationColumn: any = {
    field: "separation",
    headerName: "Separation",
    flex: 1,
    minWidth: 110,
    filterable: false,
    renderCell: (params: any) =>
      params.value != null ? `${params.value.toFixed(2)}"` : "",
  };

  const mlScoreColumn = (field: string, headerName: string): any => ({
    field,
    headerName,
    flex: 1,
    minWidth: 90,
    filterable: false,
    headerClassName: compactHeaderClass,
    cellClassName: compactHeaderClass,
    renderCell: (params: any) => params.value?.toFixed(2),
  });

  const surveyColumns: any[] = [
    {
      field: "jd",
      headerName: isLSST ? "MJD" : "JD",
      flex: 1,
      minWidth: 110,
      filterable: false,
      sortingOrder: ["desc", "asc", null],
      renderCell: (params: any) => params.value?.toFixed(5),
    },
    ...positionColumns,
    {
      field: "band",
      headerName: "band",
      flex: 1,
      minWidth: 80,
      headerClassName: compactHeaderClass,
    },
    {
      field: "magpsf",
      headerName: "magpsf",
      flex: 1,
      minWidth: 130,
      filterable: false,
      cellClassName: "alerts-nowrap-cell",
      renderCell: (params: any) => {
        const mag = params.row.magpsf;
        const sigma = params.row.sigmapsf;
        if (mag == null) return "—";
        return sigma != null
          ? `${mag.toFixed(3)} ± ${sigma.toFixed(3)}`
          : mag.toFixed(3);
      },
    },
    {
      field: "snr",
      headerName: "snr",
      flex: 1,
      minWidth: 80,
      filterable: false,
      headerClassName: compactHeaderClass,
      cellClassName: compactHeaderClass,
      renderCell: (params: any) => params.value?.toFixed(2),
    },
    {
      field: "isdiffpos",
      headerName: "isdiffpos",
      flex: 1,
      minWidth: 100,
      renderCell: (params: any) =>
        params.value != null ? String(params.value) : "—",
    },
    {
      field: "drb",
      headerName: isLSST ? "reliability" : isZTF ? "drb" : "scorr",
      flex: 1,
      minWidth: 100,
      filterable: false,
      headerClassName: compactHeaderClass,
      cellClassName: compactHeaderClass,
      renderCell: (params: any) => params.value?.toFixed(2),
    },
    ...(!isLSST
      ? [
          {
            field: "programid",
            headerName: "programid",
            flex: 1,
            minWidth: 100,
            headerClassName: compactHeaderClass,
          },
        ]
      : []),
    // ACAI/BTSbot are ZTF-specific classifiers; don't show them for other surveys.
    ...(isZTF
      ? [
          mlScoreColumn("acai_h", "acai_h"),
          mlScoreColumn("acai_n", "acai_n"),
          mlScoreColumn("acai_o", "acai_o"),
          mlScoreColumn("acai_v", "acai_v"),
          mlScoreColumn("acai_b", "acai_b"),
          mlScoreColumn("btsbot", "BTSbot"),
        ]
      : []),
  ];

  const columns: any[] = [
    expandColumn,
    objectIdColumn,
    candidColumn,
    ...surveyColumns,
  ];

  if (groupByObj) {
    const { ra, dec, object_id } = getValues();
    if (ra && dec && !object_id) {
      // insert separation after the dec column
      // (index 5: __expand, objectId, candid, jd, ra, dec)
      columns.splice(6, 0, separationColumn);
    }
  }

  // sigmapsf is folded into the magpsf cell, so it is never shown as its own
  // column (matches the old display:false). candid stays visible as before.
  const columnVisibilityModel = { sigmapsf: false };

  // Default sort: separation ascending in positional grouped mode, otherwise
  // most-recent (jd) first.
  const useSeparationSort =
    groupByObj && getValues()["ra"] && getValues()["dec"];
  const sortModel: any[] = [
    useSeparationSort
      ? { field: "separation", sort: "asc" }
      : { field: "jd", sort: "desc" },
  ];

  // Interleave a synthetic full-width detail row after each expanded alert so
  // the cutout-triplet pull-out renders inline (DataGrid community edition has
  // no native master-detail). getRowHeight lets those rows size to content.
  const displayRows: any[] = [];
  rows.forEach((row: any) => {
    displayRows.push(row);
    if (openedRows.includes(row.candid)) {
      displayRows.push({ candid: row.candid, __detail: true, __source: row });
    }
  });

  const getRowHeight = (params: any) => (params.model.__detail ? "auto" : null);

  const CustomToolbar = () => (
    <GridToolbarContainer>
      <GridToolbarColumnsButton />
      <FormControlLabel
        control={
          <Switch
            checked={groupByObj}
            onChange={() => setGroupByObj(!groupByObj)}
            name="groupAlerts"
            color="primary"
          />
        }
        label="Group by Object ID"
      />
      {groupByObj && selectedRowIds.length > 0 && (
        <Tooltip title="Save selected alerts as sources">
          <IconButton
            aria-label="save"
            data-testid="save-selected-alerts-button"
            onClick={() => {
              const objectIds = Array.from(
                new Set(
                  selectedRowIds
                    .map((rowId: any) => objectIdByRowId[rowId])
                    .filter(Boolean),
                ),
              );
              handleSaveDialogOpen(objectIds);
            }}
            size="large"
          >
            <SaveIcon />
          </IconButton>
        </Tooltip>
      )}
    </GridToolbarContainer>
  );

  const formSubmit = async () => {
    let { object_id, ra, dec, radius, radius_unit, instrument } = getValues();
    let survey = (instrument || "ztf").toUpperCase();

    if (object_id?.trim()) {
      const inferred = inferSurvey(object_id.trim());
      if (inferred && inferred !== survey) {
        survey = inferred;
        setValue("instrument", inferred.toLowerCase());
        dispatch(
          showNotification(
            `Survey changed to ${inferred} based on the object ID format.`,
            "warning",
          ),
        );
      }
    }

    setSelectedSurvey(survey);
    ra = ra?.toString();
    dec = dec?.toString();
    radius = radius?.toString();

    if (!object_id?.length && !ra?.length && !dec?.length && !radius?.length) {
      dispatch(
        showNotification(
          `You must either specify an object ID, a position`,
          "error",
        ),
      );
      return;
    }

    if (object_id?.length) {
      object_id = object_id.trim();
    }

    // check that if positional query is requested then all required data are supplied
    if (
      (ra?.length || dec?.length || radius?.length) &&
      !(ra?.length && dec?.length && radius?.length)
    ) {
      dispatch(
        showNotification(
          `Positional parameters, if specified, must be all set`,
          "error",
        ),
      );
    } else {
      const hadPositionalParams = !!(
        ra?.length ||
        dec?.length ||
        radius?.length
      );
      if (ra?.length) {
        if (
          ra?.includes(":") ||
          ra?.includes("h") ||
          ra?.includes("m") ||
          ra?.includes("s")
        ) {
          ra = ra.replace(/h|m/g, ":").replace(/s/g, "");
          ra = hours_to_ra(ra);
        } else {
          ra = parseFloat(ra);
        }
      }
      if (dec?.length) {
        if (
          dec?.includes(":") ||
          dec?.includes("d") ||
          dec?.includes("m") ||
          dec?.includes("s")
        ) {
          dec = dec.replace(/d|m/g, ":").replace(/s/g, "");
          dec = dms_to_dec(dec);
        } else {
          dec = parseFloat(dec);
        }
      }
      if (radius_unit === "arcmin") {
        //convert arcmin to arcsec
        radius = parseFloat(radius) * 60;
      } else if (radius_unit === "deg") {
        //convert deg to arcsec
        radius = parseFloat(radius) * 3600;
      } else if (radius_unit === "rad") {
        //convert rad to arcsec
        radius = parseFloat(radius) * 206264.80624709636;
      } else {
        radius = parseFloat(radius);
      }

      if (object_id?.length) {
        if (hadPositionalParams) {
          dispatch(
            showNotification(
              `Object ID specified, ignored positional parameters`,
              "warning",
            ),
          );
        }
        ra = null;
        dec = null;
        radius = null;
      } else if (
        Number.isNaN(parseFloat(ra)) ||
        Number.isNaN(parseFloat(dec)) ||
        Number.isNaN(parseFloat(radius))
      ) {
        dispatch(showNotification(`Invalid positional parameters`, "error"));
        return;
      }
      if (object_id?.indexOf(",") > -1) {
        const object_id_split = object_id.split(",");
        triggerGetAlerts({
          survey,
          object_id: object_id_split,
          ra,
          dec,
          radius,
        } as any);
      } else {
        triggerGetAlerts({ survey, object_id, ra, dec, radius } as any);
      }
    }
  };

  return (
    <>
      <div>
        <Grid
          container
          direction="row"
          spacing={1}
          sx={{ justifyContent: "flex-start", alignItems: "flex-start" }}
        >
          <Grid size={{ xs: 12, lg: 10 }} className={classes.grid_item_table}>
            <Paper elevation={1}>
              <div className={(classes as any).maindiv}>
                <div className={(classes as any).accordionDetails}>
                  <Typography variant="h6" style={{ padding: "0.5rem" }}>
                    {groupByObj ? "Alerts (grouped by Object ID)" : "Alerts"}
                  </Typography>
                  {queryInProgress ? (
                    <CircularProgress />
                  ) : (
                    <StyledDataGrid
                      autoHeight
                      rows={displayRows}
                      columns={columns}
                      getRowId={getRowId}
                      getRowHeight={getRowHeight}
                      columnVisibilityModel={columnVisibilityModel}
                      sortModel={sortModel}
                      checkboxSelection={groupByObj}
                      isRowSelectable={(params: any) => !params.row.__detail}
                      rowSelectionModel={{
                        type: "include",
                        ids: new Set(selectedRowIds),
                      }}
                      onRowSelectionModelChange={(model: any) =>
                        setSelectedRowIds(Array.from(model.ids))
                      }
                      // Keep all columns mounted so the detail row's colSpan
                      // works (column virtualization conflicts with colSpan).
                      columnBufferPx={3000}
                      pageSizeOptions={[10, 25, 50, 100]}
                      initialState={{
                        pagination: { paginationModel: { pageSize: 10 } },
                      }}
                      slots={{ toolbar: CustomToolbar }}
                      showToolbar
                      sx={{
                        "& .alerts-compact-cell": {
                          padding: "4px 4px 4px 4px",
                        },
                        "& .alerts-nowrap-cell": {
                          whiteSpace: "nowrap",
                        },
                      }}
                    />
                  )}
                </div>
              </div>
            </Paper>
          </Grid>
          <Grid
            size={{ xs: 12, lg: 2 }}
            className={classes.grid_item_search_box}
          >
            <Card className={classes.root}>
              <form onSubmit={handleSubmit(formSubmit)}>
                <CardContent className={classes.cardContent}>
                  <FormControl required className={classes.selectEmpty}>
                    <InputLabel
                      {...({
                        name: "alert-stream-select-required-label",
                      } as any)}
                    >
                      Instrument
                    </InputLabel>
                    <Controller
                      {...({
                        labelId: "alert-stream-select-required-label",
                      } as any)}
                      name="instrument"
                      control={control}
                      rules={{ required: true }}
                      render={({ field: { onChange, value } }) => (
                        <Select
                          value={value || "ztf"}
                          onChange={(e) => {
                            onChange(e);
                          }}
                          defaultValue="ztf"
                        >
                          <MenuItem value="ztf">ZTF</MenuItem>
                          <MenuItem value="lsst">LSST</MenuItem>
                          <MenuItem value="winter">WINTER</MenuItem>
                        </Select>
                      )}
                    />
                    <FormHelperText>Required</FormHelperText>
                  </FormControl>
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <TextField
                        autoFocus
                        margin="dense"
                        name="object_id"
                        label="objectId"
                        type="text"
                        fullWidth
                        inputRef={
                          register("object_id", {
                            minLength: 3,
                            required: false,
                          }) as any
                        }
                        value={value}
                        onChange={onChange}
                      />
                    )}
                    name="object_id"
                    control={control}
                  />
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <TextField
                        margin="dense"
                        name="ra"
                        label="RA [deg, HH:MM:SS, HHhMMmSSs]"
                        fullWidth
                        inputRef={register("ra", { required: false }) as any}
                        value={value}
                        onChange={onChange}
                      />
                    )}
                    name="ra"
                    control={control}
                  />
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <TextField
                        margin="dense"
                        name="dec"
                        label="Dec [deg, DD:MM:SS, DDdMMmSSs]"
                        fullWidth
                        inputRef={register("dec", { required: false }) as any}
                        value={value}
                        onChange={onChange}
                      />
                    )}
                    name="dec"
                    control={control}
                  />
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "row",
                      justifyContent: "space-between",
                      gap: "0.5rem",
                    }}
                  >
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <TextField
                          margin="dense"
                          name="radius"
                          label="Radius"
                          fullWidth
                          inputRef={
                            register("radius", { required: false }) as any
                          }
                          value={value}
                          onChange={onChange}
                        />
                      )}
                      name="radius"
                      control={control}
                    />
                    <Controller
                      {...({
                        labelId: "radius-unit-select-required-label",
                      } as any)}
                      name="radius_unit"
                      control={control}
                      rules={{ required: true }}
                      render={({ field: { onChange, value } }) => (
                        <Select
                          value={value}
                          onChange={onChange}
                          defaultValue="arcsec"
                          inputRef={
                            register("radius_unit", { required: true }) as any
                          }
                          {...({ margin: "dense" } as any)}
                          fullWidth
                          style={{
                            height: "3.5rem",
                            marginTop: "8px",
                            marginBottom: "4px",
                          }}
                        >
                          <MenuItem value="arcsec">arcsec</MenuItem>
                          <MenuItem value="arcmin">arcmin</MenuItem>
                          <MenuItem value="deg">deg</MenuItem>
                          <MenuItem value="rad">rad</MenuItem>
                        </Select>
                      )}
                    />
                  </div>
                </CardContent>
                <CardActions className={classes.cardActions}>
                  <div className={classes.wrapperRoot}>
                    <div className={classes.wrapper}>
                      <Button
                        type="submit"
                        variant="contained"
                        color="primary"
                        onClick={() => formSubmit()}
                        disabled={queryInProgress}
                      >
                        Search
                      </Button>
                      {queryInProgress && (
                        <CircularProgress
                          size={24}
                          color="secondary"
                          className={classes.buttonProgress}
                        />
                      )}
                    </div>
                  </div>
                </CardActions>
              </form>
            </Card>
          </Grid>
        </Grid>
        <Dialog
          open={saveDialogOpen}
          onClose={handleSaveDialogClose}
          aria-labelledby="responsive-dialog-title"
          maxWidth="md"
        >
          <DialogTitle id="responsive-dialog-title">
            Save Alert(s) as Source(s)
          </DialogTitle>
          <DialogContent>
            <DialogContentText>
              Save the following alert(s) as source(s) to the selected group(s):
            </DialogContentText>
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                flexWrap: "wrap",
                width: "100%",
              }}
            >
              {(rowsToSave || []).map((objectId: any) => (
                <Chip key={objectId} label={`${objectId}`} />
              ))}
            </div>
            <DialogContentText className={classes.marginTop}>
              Select groups to save new source to:
            </DialogContentText>
            {selectedGroups?.length === 0 && (
              <FormValidationError message="Select at least one group." />
            )}
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                flexWrap: "wrap",
                width: "100%",
              }}
            >
              {groups.map((group: any) => (
                <div key={group.id}>
                  <Checkbox
                    color="primary"
                    checked={selectedGroups.includes(group.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedGroups((prev) => [...prev, group.id]);
                      } else {
                        setSelectedGroups(
                          selectedGroups.filter((g: any) => g !== group.id),
                        );
                      }
                    }}
                  />
                  {group.nickname || group.name}
                </div>
              ))}
            </div>
          </DialogContent>
          <DialogActions>
            <Button
              variant="contained"
              color="primary"
              className={classes.search_button}
              type="submit"
              data-testid="save-dialog-submit"
              onClick={() => handleSave()}
              disabled={
                selectedGroups?.length === 0 ||
                rowsToSave?.length === 0 ||
                saving
              }
            >
              Save
            </Button>
            <Button
              autoFocus
              onClick={handleSaveDialogClose}
              color="primary"
              disabled={saving}
            >
              Dismiss
            </Button>
          </DialogActions>
        </Dialog>
      </div>
    </>
  );
};

export default Alerts;
