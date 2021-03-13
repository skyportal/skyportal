import React, { useEffect, useState, Suspense } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useHistory } from "react-router-dom";

import Button from "@material-ui/core/Button";
import PropTypes from "prop-types";
import {
  makeStyles,
  useTheme,
  createMuiTheme,
  MuiThemeProvider,
} from "@material-ui/core/styles";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import Accordion from "@material-ui/core/Accordion";
import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";
import Typography from "@material-ui/core/Typography";
import CircularProgress from "@material-ui/core/CircularProgress";
import Chip from "@material-ui/core/Chip";
import OpenInNewIcon from "@material-ui/icons/OpenInNew";

import MUIDataTable from "mui-datatables";
import ReactJson from "react-json-view";

import SaveAlertButton from "./SaveAlertButton";
import ThumbnailList from "./ThumbnailList";

import { ra_to_hours, dec_to_dms } from "../units";
import SharePage from "./SharePage";

import * as Actions from "../ducks/alert";

const VegaPlotZTFAlert = React.lazy(() => import("./VegaPlotZTFAlert"));

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
  },
  container: {
    maxHeight: 440,
  },
  whitish: {
    color: "#f0f0f0",
  },
  itemPaddingBottom: {
    paddingBottom: "0.5rem",
  },
  saveAlertButton: {
    margin: "0.5rem 0",
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
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
  header: {
    paddingBottom: "0.625rem",
    color: theme.palette.text.primary,
  },

  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  accordionDetails: {
    width: "100%",
  },
  source: {
    padding: "1rem",
    display: "flex",
    flexDirection: "row",
  },
  column: {
    display: "flex",
    flexFlow: "column nowrap",
    verticalAlign: "top",
    flex: "0 2 100%",
    minWidth: 0,
  },
  columnItem: {
    margin: "0.5rem 0",
  },
  name: {
    fontSize: "200%",
    fontWeight: "900",
    color: "darkgray",
    paddingBottom: "0.25em",
    display: "inline-block",
  },
  alignRight: {
    display: "inline-block",
    verticalAlign: "super",
  },
  sourceInfo: {
    display: "flex",
    flexFlow: "row wrap",
    alignItems: "center",
  },
  position: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

function isString(x) {
  return Object.prototype.toString.call(x) === "[object String]";
}

const getMuiTheme = (theme) =>
  createMuiTheme({
    overrides: {
      MUIDataTableBodyCell: {
        root: {
          padding: `${theme.spacing(0.25)}px 0px ${theme.spacing(
            0.25
          )}px ${theme.spacing(1)}px`,
        },
      },
    },
  });

const ZTFAlert = ({ route }) => {
  const objectId = route.id;
  const dispatch = useDispatch();
  const history = useHistory();

  // figure out if this objectId has been saved as Source.
  const [savedSource, setsavedSource] = useState(false);
  const [checkedIfSourceSaved, setsCheckedIfSourceSaved] = useState(false);

  // not using API/source duck as that would throw an error if source does not exist
  const fetchInit = {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
    },
    method: "GET",
  };

  const loadedSourceId = useSelector((state) => state?.source?.id);

  useEffect(() => {
    const fetchSource = async () => {
      const response = await fetch(`/api/sources/${objectId}`, fetchInit);

      let json = "";
      try {
        json = await response.json();
      } catch (error) {
        throw new Error(`JSON decoding error: ${error}`);
      }

      if (json.status === "success") {
        setsavedSource(true);
      }
      setsCheckedIfSourceSaved(true);
    };

    if (!checkedIfSourceSaved) {
      fetchSource();
    }
  }, [objectId, dispatch, fetchInit]);

  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible
  );

  const userAccessibleGroupIds = useSelector((state) =>
    state.groups.userAccessible?.map((a) => a.id)
  );

  const theme = useTheme();
  const darkTheme = theme.palette.type === "dark";

  const [
    panelPhotometryThumbnailsExpanded,
    setPanelPhotometryThumbnailsExpanded,
  ] = useState(true);

  const handlePanelPhotometryThumbnailsChange = (panel) => (
    event,
    isExpanded
  ) => {
    setPanelPhotometryThumbnailsExpanded(isExpanded ? panel : false);
  };

  const [panelXMatchExpanded, setPanelXMatchExpanded] = useState(true);

  const handlePanelXMatchChange = (panel) => (event, isExpanded) => {
    setPanelXMatchExpanded(isExpanded ? panel : false);
  };

  const [panelAlertsExpanded, setPanelAlertsExpanded] = useState(true);
  const handlePanelAlertsExpandedChange = (panel) => (event, isExpanded) => {
    setPanelAlertsExpanded(isExpanded ? panel : false);
  };

  const [candid, setCandid] = useState(0);
  const [jd, setJd] = useState(0);

  const alert_data = useSelector((state) => state.alert_data);

  const makeRow = (alert) => {
    return {
      candid: alert?.candid,
      jd: alert?.candidate.jd,
      fid: alert?.candidate.fid,
      mag: alert?.candidate.magpsf,
      emag: alert?.candidate.sigmapsf,
      rb: alert?.candidate.rb,
      drb: alert?.candidate.drb,
      isdiffpos: alert?.candidate.isdiffpos,
      programid: alert?.candidate.programid,
      alert_actions: "show thumbnails",
    };
  };

  let rows = [];

  if (alert_data !== null && !isString(alert_data)) {
    rows = alert_data?.map((a) => makeRow(a));
  }

  const alert_aux_data = useSelector((state) => state.alert_aux_data);
  let cross_matches = {};

  if (alert_aux_data !== null && !isString(alert_aux_data)) {
    cross_matches = alert_aux_data.cross_matches;
    // const fids = Array.from(new Set(prv_candidates.map(c => c.fid)))
  }

  const cachedObjectId =
    alert_data !== null && !isString(alert_data) && candid > 0
      ? route.id
      : null;

  const isCached = route.id === cachedObjectId;

  useEffect(() => {
    const fetchAlert = async () => {
      const data = await dispatch(Actions.fetchAlertData(objectId));
      if (data.status === "success") {
        // fetch aux data
        await dispatch(Actions.fetchAuxData(objectId));

        const candids = Array.from(
          new Set(data.data.map((c) => c.candid))
        ).sort();
        const jds = Array.from(
          new Set(data.data.map((c) => c.candidate.jd))
        ).sort();
        // grab the latest candid's thumbnails by default
        setCandid(candids[candids.length - 1]);
        setJd(jds[jds.length - 1]);
      }
    };

    if (!isCached) {
      fetchAlert();
    }
  }, [dispatch, isCached, route.id, objectId]);

  const classes = useStyles();

  const thumbnails = [
    {
      type: "new",
      id: 0,
      public_url: `/api/alerts/ztf/${objectId}/cutout?candid=${candid}&cutout=science&file_format=png`,
    },
    {
      type: "ref",
      id: 1,
      public_url: `/api/alerts/ztf/${objectId}/cutout?candid=${candid}&cutout=template&file_format=png`,
    },
    {
      type: "sub",
      id: 2,
      public_url: `/api/alerts/ztf/${objectId}/cutout?candid=${candid}&cutout=difference&file_format=png`,
    },
    // {
    //   type: "sdss",
    //   id: 3,
    //   public_url: `http://skyserver.sdss.org/dr12/SkyserverWS/ImgCutout/getjpeg?ra=${alert_data.filter((a) => a.candid === candid)[0].candidate.ra}&dec=${alert_data.filter((a) => a.candid === candid)[0].candidate.dec}&scale=0.3&width=200&height=200&opt=G&query=&Grid=on`
    // },
    // {
    //   type: "dr8",
    //   id: 4,
    //   public_url: `http://legacysurvey.org/viewer/jpeg-cutout?ra=${alert_data.filter((a) => a.candid === candid)[0].candidate.ra}&dec=${alert_data.filter((a) => a.candid === candid)[0].candidate.dec}&size=200&layer=dr8&pixscale=0.262&bands=grz`
    // },
  ];

  const options = {
    selectableRows: "none",
    elevation: 1,
    sortOrder: {
      name: "jd",
      direction: "desc",
    },
  };

  const columns = [
    {
      name: "candid",
      label: "candid",
      options: {
        filter: false,
        sort: true,
        sortDescFirst: true,
      },
    },
    {
      name: "jd",
      label: "JD",
      options: {
        filter: false,
        sort: true,
        sortDescFirst: true,
        customBodyRender: (value, tableMeta, updateValue) => value.toFixed(5),
      },
    },
    {
      name: "fid",
      label: "fid",
      options: {
        filter: true,
        sort: true,
      },
    },
    {
      name: "mag",
      label: "mag",
      options: {
        filter: false,
        sort: true,
        customBodyRender: (value, tableMeta, updateValue) => value.toFixed(3),
      },
    },
    {
      name: "emag",
      label: "e_mag",
      options: {
        filter: false,
        sort: true,
        customBodyRender: (value, tableMeta, updateValue) => value.toFixed(3),
      },
    },
    {
      name: "rb",
      label: "rb",
      options: {
        filter: false,
        sort: true,
        sortDescFirst: true,
        customBodyRender: (value, tableMeta, updateValue) => value.toFixed(5),
      },
    },
    {
      name: "drb",
      label: "drb",
      options: {
        filter: false,
        sort: true,
        sortDescFirst: true,
        customBodyRender: (value, tableMeta, updateValue) => value?.toFixed(5),
      },
    },
    {
      name: "isdiffpos",
      label: "isdiffpos",
      options: {
        filter: true,
        sort: true,
      },
    },
    {
      name: "programid",
      label: "programid",
      options: {
        filter: true,
        sort: true,
      },
    },
    {
      name: "alert_actions",
      label: "actions",
      options: {
        filter: false,
        sort: false,
        customBodyRender: (value, tableMeta, updateValue) => (
          <Button
            size="small"
            onClick={() => {
              setCandid(tableMeta.rowData[0]);
              setJd(tableMeta.rowData[1]);
            }}
          >
            Show&nbsp;thumbnails
          </Button>
        ),
      },
    },
  ];

  if (alert_data === null) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  if (isString(alert_data) || isString(alert_aux_data)) {
    return <div>Failed to fetch alert data, please try again later.</div>;
  }
  if (alert_data.length === 0) {
    return (
      <div>
        <Typography variant="h5" className={classes.header}>
          {objectId} not found
        </Typography>
      </div>
    );
  }
  if (alert_data.length > 0) {
    return (
      <Paper elevation={1} className={classes.source}>
        <div className={classes.column}>
          <div className={classes.leftColumnItem}>
            <div className={classes.alignRight}>
              <SharePage />
            </div>
            <div className={classes.name}>{objectId}</div>
            <br />
            {savedSource || loadedSourceId === objectId ? (
              <div className={classes.itemPaddingBottom}>
                <Chip
                  size="small"
                  label="Previously Saved"
                  clickable
                  onClick={() => history.push(`/source/${objectId}`)}
                  onDelete={() => window.open(`/source/${objectId}`, "_blank")}
                  deleteIcon={<OpenInNewIcon />}
                  color="primary"
                />
              </div>
            ) : (
              <div className={classes.itemPaddingBottom}>
                <Chip size="small" label="NOT SAVED" />
                <br />
                <div className={classes.saveAlertButton}>
                  <SaveAlertButton
                    alert={{
                      id: objectId,
                      candid: parseInt(candid),
                      group_ids: userAccessibleGroupIds,
                    }}
                    userGroups={userAccessibleGroups}
                  />
                </div>
              </div>
            )}
            {candid > 0 && (
              <>
                <b>candid:</b>
                &nbsp;
                {candid}
                <br />
                <div className={classes.sourceInfo}>
                  <div>
                    <b>Position (J2000):&nbsp; &nbsp;</b>
                  </div>
                  <div>
                    <span className={classes.position}>
                      {ra_to_hours(
                        alert_data.filter((a) => a.candid === candid)[0]
                          .candidate.ra,
                        ":"
                      )}
                      &nbsp;
                      {dec_to_dms(
                        alert_data.filter((a) => a.candid === candid)[0]
                          .candidate.dec,
                        ":"
                      )}
                      &nbsp;
                    </span>
                  </div>
                </div>
                <div className={classes.sourceInfo}>
                  <div>
                    (&alpha;,&delta;={" "}
                    {
                      alert_data.filter((a) => a.candid === candid)[0].candidate
                        .ra
                    }
                    , &nbsp;
                    {
                      alert_data.filter((a) => a.candid === candid)[0].candidate
                        .dec
                    }
                    ; &nbsp;
                  </div>
                  {candid > 0 &&
                    alert_data.filter((a) => a.candid === candid)[0].coordinates
                      .b && (
                      <div>
                        &nbsp; l,b=
                        {alert_data
                          .filter((a) => a.candid === candid)[0]
                          .coordinates?.l?.toFixed(6)}
                        , &nbsp;
                        {alert_data
                          .filter((a) => a.candid === candid)[0]
                          .coordinates?.b?.toFixed(6)}
                        )
                      </div>
                    )}
                </div>
              </>
            )}
          </div>

          <Accordion
            expanded={panelPhotometryThumbnailsExpanded}
            onChange={handlePanelPhotometryThumbnailsChange(true)}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="panel-content"
              id="photometry-panel-header"
            >
              <Typography className={classes.accordionHeading}>
                Photometry and cutouts
              </Typography>
            </AccordionSummary>
            <AccordionDetails className={classes.accordionDetails}>
              <Grid container spacing={2}>
                <Grid item xs={12} lg={6}>
                  <Suspense fallback={<CircularProgress color="secondary" />}>
                    <VegaPlotZTFAlert
                      dataUrl={`/api/alerts/ztf/${objectId}/aux`}
                      jd={jd}
                    />
                  </Suspense>
                </Grid>
                <Grid
                  container
                  item
                  xs={12}
                  lg={6}
                  spacing={1}
                  className={classes.image}
                  alignItems="stretch"
                  alignContent="stretch"
                >
                  {candid > 0 && (
                    <ThumbnailList
                      ra={
                        alert_data.filter((a) => a.candid === candid)[0]
                          .candidate.ra
                      }
                      dec={
                        alert_data.filter((a) => a.candid === candid)[0]
                          .candidate.dec
                      }
                      thumbnails={thumbnails}
                      displayTypes={["new", "ref", "sub"]}
                      size="10rem"
                    />
                  )}
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          <Accordion
            expanded={panelAlertsExpanded}
            onChange={handlePanelAlertsExpandedChange(true)}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="panel-content"
              id="alerts-panel-header"
            >
              <Typography className={classes.accordionHeading}>
                Alerts
              </Typography>
            </AccordionSummary>
            <AccordionDetails className={classes.accordionDetails}>
              <div className={classes.accordionDetails}>
                <MuiThemeProvider theme={getMuiTheme(theme)}>
                  <MUIDataTable
                    data={rows}
                    columns={columns}
                    options={options}
                  />
                </MuiThemeProvider>
              </div>
            </AccordionDetails>
          </Accordion>

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
              <ReactJson
                src={cross_matches}
                name={false}
                theme={darkTheme ? "monokai" : "rjv-default"}
              />
            </AccordionDetails>
          </Accordion>
        </div>
      </Paper>
    );
  }
  return <div>Error rendering page...</div>;
};

ZTFAlert.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default ZTFAlert;
