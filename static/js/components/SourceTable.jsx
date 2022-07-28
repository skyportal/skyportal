import React, { Suspense, useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link, useNavigate } from "react-router-dom";

import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";
import IconButton from "@mui/material/IconButton";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import MUIDataTable from "mui-datatables";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
  adaptV4Theme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import CheckIcon from "@mui/icons-material/Check";
import ClearIcon from "@mui/icons-material/Clear";
import InfoIcon from "@mui/icons-material/Info";
import QuestionMarkIcon from "@mui/icons-material/QuestionMark";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import Collapse from "@mui/material/Collapse";
import List from "@mui/material/List";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { isMobileOnly } from "react-device-detect";

import { ra_to_hours, dec_to_dms, mjd_to_utc } from "../units";
import ThumbnailList from "./ThumbnailList";
import ShowClassification from "./ShowClassification";
import SourceTableFilterForm from "./SourceTableFilterForm";
import VegaPhotometry from "./VegaPhotometry";
import FavoritesButton from "./FavoritesButton";
import MultipleClassificationsForm from "./MultipleClassificationsForm";
import * as sourceActions from "../ducks/source";
import * as sourcesActions from "../ducks/sources";
import * as sourcesingcnActions from "../ducks/confirmedsourcesingcn";
import { filterOutEmptyValues } from "../API";
import { getAnnotationValueString } from "./ScanningPageCandidateAnnotations";
import ConfirmSourceInGCN from "./ConfirmSourceInGCN";

const VegaSpectrum = React.lazy(() => import("./VegaSpectrum"));
const VegaHR = React.lazy(() => import("./VegaHR"));

const useStyles = makeStyles((theme) => ({
  comment: {
    fontSize: "90%",
    display: "flex",
    flexDirection: "row",
    padding: "0.125rem",
    margin: "0 0.125rem 0.125rem 0",
    borderRadius: "1rem",
    "&:hover": {
      backgroundColor: "#e0e0e0",
    },
    "& .commentDelete": {
      "&:hover": {
        color: "#e63946",
      },
    },
  },
  commentDark: {
    fontSize: "90%",
    display: "flex",
    flexDirection: "row",
    padding: "0.125rem",
    margin: "0 0.125rem 0.125rem 0",
    borderRadius: "1rem",
    "&:hover": {
      backgroundColor: "#3a3a3a",
    },
    "& .commentDelete": {
      color: "#b1dae9",
      "&:hover": {
        color: "#e63946",
      },
    },
  },
  commentUserAvatar: {
    display: "block",
    margin: "0.5em",
  },
  commentContent: {
    display: "flex",
    flexFlow: "column nowrap",
    padding: "0.3125rem 0.625rem 0.3125rem 0.875rem",
    borderRadius: "15px",
    width: "100%",
  },
  commentHeader: {
    display: "flex",
    alignItems: "center",
  },
  commentUserName: {
    fontWeight: "bold",
    marginRight: "0.5em",
    whiteSpace: "nowrap",
    color: "#76aace",
  },
  commentTime: {
    color: "gray",
    fontSize: "80%",
    marginRight: "1em",
  },
  commentUserGroup: {
    display: "inline-block",
    "& > svg": {
      fontSize: "1rem",
    },
  },
  commentMessage: {
    maxWidth: "25em",
    "& > p": {
      margin: "0",
    },
  },
  wrap: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    minHeight: "27px",
    maxWidth: "25em",
  },
  chip: {
    margin: theme.spacing(0.5),
  },
  source: {},
  commentListContainer: {
    height: "15rem",
    overflowY: "scroll",
    padding: "0.5rem 0",
  },
  tableGrid: {
    width: "100%",
  },
  groupSelect: {
    maxWidth: "20rem",
  },
  filterFormRow: {
    margin: "0.75rem 0",
  },
  sourceName: {
    verticalAlign: "middle",
  },
  objId: {
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
  },
  starButton: {
    verticalAlign: "middle",
  },
  filterAlert: {
    marginTop: "1rem",
    display: "flex",
    alignItems: "center",
    fontSize: "1rem",
  },
  annotations: (props) => ({
    minWidth: props.annotationsMinWidth,
    maxWidth: props.annotationsMaxWidth,
    overflowWrap: "break-word",
  }),
  root: {
    width: "100%",
    background: theme.palette.background.paper,
    padding: theme.spacing(1),
    maxHeight: "15rem",
    overflowY: "scroll",
  },
  nested: {
    paddingLeft: theme.spacing(4),
    paddingTop: 0,
    paddingBottom: 0,
  },
}));

const getMuiTheme = (theme) =>
  createTheme(
    adaptV4Theme({
      palette: theme.palette,
      overrides: {
        MUIDataTableHeadCell: {
          sortLabelRoot: {
            height: "1.4rem",
          },
        },
        // Hide default filter items for custom form
        MuiGridList: {
          root: {
            display: "none",
          },
        },
        MUIDataTableFilter: {
          root: {
            height: "100%",
          },
          header: {
            display: "none",
          },
        },
        MUIDataTablePagination: {
          toolbar: {
            flexFlow: "row wrap",
            justifyContent: "flex-end",
            padding: "0.5rem 1rem 0",
            [theme.breakpoints.up("sm")]: {
              // Cancel out small screen styling and replace
              padding: "0px",
              paddingRight: "2px",
              flexFlow: "row nowrap",
            },
          },
          navContainer: {
            flexDirection: "column",
            alignItems: "center",
            [theme.breakpoints.up("sm")]: {
              flexDirection: "row",
            },
          },
          selectRoot: {
            marginRight: "0.5rem",
            [theme.breakpoints.up("sm")]: {
              marginLeft: "0",
              marginRight: "2rem",
            },
          },
        },
        MUIDataTableToolbar: {
          filterPaper: {
            // Use fullscreen dialog for small-screen filter form
            width: "100%",
            maxWidth: "100%",
            margin: 0,
            maxHeight: "calc(100vh - 1rem)",
            borderRadius: 0,
            top: "0 !important",
            left: "0 !important",
            [theme.breakpoints.up("md")]: {
              // Override the overrides above for bigger screens
              maxWidth: "50%",
              top: "unset !important",
              left: "unset !important",
              float: "right",
              position: "unset",
              margin: "1rem",
            },
          },
          filterCloseIcon: {
            [theme.breakpoints.up("md")]: {
              top: "1rem !important",
              right: "1rem !important",
            },
          },
        },
        MUIDataTableFilterList: {
          chip: {
            maxWidth: "100%",
          },
        },
      },
    })
  );

let defaultDisplayedColumns = [
  "Source ID",
  "Favorites",
  "RA (deg)",
  "Dec (deg)",
  "Redshift",
  "Classification",
  "Groups",
  "Date Saved",
  "Finder",
];

// MUI data table with pull out rows containing a summary of each source.
// This component is used in GroupSources, SourceList and Favorites page.
const SourceTable = ({
  sources,
  title,
  sourceStatus = "saved",
  groupID,
  paginateCallback,
  pageNumber,
  totalMatches,
  numPerPage,
  sortingCallback,
  favoritesRemoveButton = false,
  hideTitle = false,
  downloadCallback,
  includeGcnStatus = false,
  sourceInGcnFilter,
}) => {
  // sourceStatus should be one of either "saved" (default) or "requested" to add a button to agree to save the source.
  // If groupID is not given, show all data available to user's accessible groups

  const dispatch = useDispatch();
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const classes = useStyles();
  const theme = useTheme();

  if (favoritesRemoveButton) {
    defaultDisplayedColumns = defaultDisplayedColumns?.filter(
      (c) => c !== "Favorites"
    );
  }
  if (includeGcnStatus) {
    defaultDisplayedColumns.push("GCN Status");
  }

  const [displayedColumns, setDisplayedColumns] = useState(
    defaultDisplayedColumns
  );
  const [openedRows, setOpenedRows] = useState([]);

  const [filterFormSubmitted, setFilterFormSubmitted] = useState(false);

  const [tableFilterList, setTableFilterList] = useState([]);
  const [filterFormData, setFilterFormData] = useState(null);

  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);
  const [queryInProgress, setQueryInProgress] = useState(false);

  const gcnEvent = useSelector((state) => state.gcnEvent);
  const localization = useSelector((state) => state.localization);

  const sourcesingcn = useSelector((state) => state.sourcesingcn.sourcesingcn);

  useEffect(() => {
    if (sources) {
      setQueryInProgress(false);
      if (includeGcnStatus) {
        dispatch(
          sourcesingcnActions.fetchSourcesInGcn(gcnEvent.dateobs, {
            localizationName: localization.localization_name,
            sourcesIdList: sources.map((s) => s.id),
          })
        );
      }
    }
  }, [sources]);

  const handleTableChange = (action, tableState) => {
    switch (action) {
      case "changePage":
      case "changeRowsPerPage":
        setQueryInProgress(true);
        setRowsPerPage(tableState.rowsPerPage);
        paginateCallback(
          tableState.page + 1,
          tableState.rowsPerPage,
          tableState.sortOrder,
          filterFormData
        );
        break;
      case "viewColumnsChange":
        // Save displayed column labels
        setDisplayedColumns(
          tableState.columns
            ?.filter((column) => column.display === "true")
            ?.map((column) => column.label)
        );
        break;
      case "sort":
        if (tableState.sortOrder.direction === "none") {
          paginateCallback(1, tableState.rowsPerPage, {}, filterFormData);
        } else {
          sortingCallback(tableState.sortOrder, filterFormData);
        }
        break;
      default:
    }
  };

  const handleSaveSource = async (sourceID) => {
    const result = await dispatch(
      sourceActions.acceptSaveRequest({ sourceID, groupID })
    );
    if (result.status === "success") {
      dispatch(
        sourcesActions.fetchPendingGroupSources({
          group_ids: [groupID],
          pageNumber: 1,
          numPerPage: 10,
        })
      );
      dispatch(
        sourcesActions.fetchSavedGroupSources({
          group_ids: [groupID],
          pageNumber: 1,
          numPerPage: 10,
        })
      );
    }
  };

  const handleIgnoreSource = async (sourceID) => {
    const result = await dispatch(
      sourceActions.declineSaveRequest({ sourceID, groupID })
    );
    if (result.status === "success") {
      dispatch(
        sourcesActions.fetchPendingGroupSources({
          group_ids: [groupID],
          pageNumber: 1,
          numPerPage: 10,
        })
      );
    }
  };

  const [openedOrigins, setOpenedOrigins] = useState({});

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderPullOutRow = (rowData, rowMeta) => {
    const colSpan = rowData.length + 1;
    const source = sources[rowMeta.dataIndex];

    const annotations = source.annotations || [];

    const initState = {};
    annotations?.forEach((annotation) => {
      initState[annotation.origin] = true;
    });

    const handleClick = (origin) => {
      setOpenedOrigins({ ...openedOrigins, [origin]: !openedOrigins[origin] });
    };

    const plotWidth = isMobileOnly ? 200 : 400;
    const specPlotHeight = isMobileOnly ? 150 : 200;
    const legendOrient = isMobileOnly ? "bottom" : "right";

    return (
      <TableRow data-testid={`groupSourceExpand_${source.id}`}>
        <TableCell
          style={{ paddingBottom: 0, paddingTop: 0 }}
          colSpan={colSpan}
        >
          <Grid
            container
            direction="row"
            spacing={3}
            justifyContent="center"
            alignItems="center"
          >
            <ThumbnailList
              thumbnails={source.thumbnails}
              ra={source.ra}
              dec={source.dec}
              useGrid={false}
            />
            <Grid item>
              {source.photometry_exists && (
                <Suspense
                  fallback={
                    <div>
                      <CircularProgress color="secondary" />
                    </div>
                  }
                >
                  <VegaPhotometry sourceId={source.id} />
                </Suspense>
              )}
              {!source.photometry_exists && <div> no photometry exists </div>}
            </Grid>
            <Grid item>
              {source.photometry_exists && source.period_exists && (
                <Suspense
                  fallback={
                    <div>
                      <CircularProgress color="secondary" />
                    </div>
                  }
                >
                  <VegaPhotometry sourceId={source.id} folded />
                </Suspense>
              )}
              {!source.photometry_exists && <div> no photometry exists </div>}
            </Grid>
            <Grid item>
              {source.color_magnitude.length ? (
                <div data-testid={`hr_diagram_${source.id}`}>
                  <Suspense
                    fallback={
                      <div>
                        <CircularProgress color="secondary" />
                      </div>
                    }
                  >
                    <VegaHR
                      data={source.color_magnitude}
                      width={200}
                      height={200}
                    />
                  </Suspense>
                </div>
              ) : null}
            </Grid>
            <Grid item>
              {source.spectrum_exists && (
                <Suspense
                  fallback={
                    <div>
                      <CircularProgress color="secondary" />
                    </div>
                  }
                >
                  <VegaSpectrum
                    dataUrl={`/api/sources/${source.id}/spectra?normalization=median`}
                    width={plotWidth}
                    height={specPlotHeight}
                    legendOrient={legendOrient}
                  />
                </Suspense>
              )}
              {!source.spectrum_exists && <div> no spectra exist </div>}
            </Grid>
            <Grid item>
              <div className={classes.annotations}>
                {!!annotations && annotations.length && (
                  <>
                    <Typography variant="subtitle2">Annotations:</Typography>
                    <List
                      component="nav"
                      aria-labelledby="nested-list-subheader"
                      className={classes.root}
                      dense
                    >
                      {annotations.map((annotation) => (
                        <div key={`annotation_${annotation.origin}`}>
                          <Divider />
                          <ListItem
                            button
                            onClick={() => handleClick(annotation.origin)}
                          >
                            <ListItemText
                              primary={`${annotation.origin}`}
                              primaryTypographyProps={{ variant: "button" }}
                            />
                            {openedOrigins[annotation.origin] ? (
                              <ExpandLess />
                            ) : (
                              <ExpandMore />
                            )}
                          </ListItem>
                          <Collapse
                            in={openedOrigins[annotation.origin]}
                            timeout="auto"
                            unmountOnExit
                          >
                            <List component="div" dense disablePadding>
                              {Object.entries(annotation.data).map(
                                ([key, value]) => (
                                  <ListItem
                                    key={`key_${annotation.origin}_${key}`}
                                    button
                                    className={classes.nested}
                                  >
                                    <ListItemText
                                      secondary={`${key}: ${getAnnotationValueString(
                                        value
                                      )}`}
                                    />
                                  </ListItem>
                                )
                              )}
                            </List>
                          </Collapse>
                          <Divider />
                        </div>
                      ))}
                    </List>
                  </>
                )}
              </div>
            </Grid>
            <Grid item xs={12}>
              <MultipleClassificationsForm
                objId={source.id}
                taxonomyList={taxonomyList}
                groupId={groupID}
                currentClassifications={source.classifications}
              />
            </Grid>
            {favoritesRemoveButton ? (
              <div>
                {" "}
                <FavoritesButton sourceID={source.id} textMode />{" "}
              </div>
            ) : (
              ""
            )}
          </Grid>
        </TableCell>
      </TableRow>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderObjId = (dataIndex) => {
    const objid = sources[dataIndex].id;
    return (
      <Link
        to={`/source/${objid}`}
        key={`${objid}_objid`}
        data-testid={`${objid}`}
      >
        <span className={classes.objId}>{objid}</span>
      </Link>
    );
  };

  const renderFavoritesStar = (dataIndex) => {
    const objid = sources[dataIndex].id;
    return <FavoritesButton sourceID={objid} />;
  };

  const renderAlias = (dataIndex) => {
    const { id: objid, alias } = sources[dataIndex];

    if (alias) {
      const alias_str = Array.isArray(alias)
        ? alias.map((name) => <div key={name}> {name} </div>)
        : alias;

      return (
        <Link to={`/source/${objid}`} key={`${objid}_alias`}>
          {alias_str}
        </Link>
      );
    }
    return null;
  };

  const renderOrigin = (dataIndex) => {
    const { id: objid, origin } = sources[dataIndex];

    return (
      <Link to={`/source/${objid}`} key={`${objid}_origin`}>
        {origin}
      </Link>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.

  const renderRA = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_ra`}>{source.ra.toFixed(6)}</div>;
  };

  const renderRASex = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_ra_sex`}>{ra_to_hours(source.ra)}</div>;
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderDec = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_dec`}>{source.dec.toFixed(6)}</div>;
  };

  const renderDecSex = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_dec_sex`}>{dec_to_dms(source.dec)}</div>;
  };

  const renderClassification = (dataIndex) => {
    const source = sources[dataIndex];

    return (
      <Suspense
        fallback={
          <div>
            <CircularProgress color="secondary" />
          </div>
        }
      >
        <ShowClassification
          classifications={source.classifications}
          taxonomyList={taxonomyList}
          shortened
        />
      </Suspense>
    );
  };

  // helper function to get the source groups
  const getGroups = (source) => source.groups?.filter((group) => group.active);
  const navigate = useNavigate();

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderGroups = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <div key={`${source.id}_groups`}>
        {getGroups(source).map((group) => (
          <div key={group.name}>
            <Chip
              label={group.name.substring(0, 15)}
              key={group.id}
              size="small"
              className={classes.chip}
              onClick={() => navigate(`/group/${group.id}`)}
            />
            <br />
          </div>
        ))}
      </div>
    );
  };

  // helper function to get the source saved_at date
  const getDate = (source) => {
    if (groupID !== undefined) {
      const group = source.groups.find((g) => g.id === groupID);
      return group?.saved_at;
    }
    const dates = source.groups.map((g) => g.saved_at).sort();
    return dates[dates.length - 1];
  };

  const renderDateSaved = (dataIndex) => {
    const source = sources[dataIndex];

    return (
      <div key={`${source.id}_date_saved`}>
        {getDate(source)?.substring(0, 19)}
      </div>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderFinderButton = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <IconButton size="small" key={`${source.id}_actions`}>
        <a href={`/api/sources/${source.id}/finder`}>
          <PictureAsPdfIcon />
        </a>
      </IconButton>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderSaveIgnore = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <>
        <Button
          size="small"
          variant="contained"
          onClick={() => {
            handleSaveSource(source.id);
          }}
          data-testid={`saveSourceButton_${source.id}`}
        >
          Save
        </Button>
        &nbsp;
        <Button
          size="small"
          variant="contained"
          onClick={() => {
            handleIgnoreSource(source.id);
          }}
          data-testid={`declineRequestButton_${source.id}`}
        >
          Ignore
        </Button>
      </>
    );
  };

  const renderSpectrumExists = (dataIndex) => {
    const source = sources[dataIndex];
    return source.spectrum_exists ? (
      <CheckIcon
        size="small"
        key={`${source.id}_spectrum_exists`}
        color="primary"
      />
    ) : (
      <ClearIcon
        size="small"
        key={`${source.id}_spectrum_exists`}
        color="secondary"
      />
    );
  };

  const renderPeakMagnitude = (dataIndex) => {
    const source = sources[dataIndex];
    const photstats = source.photstats[0];
    if (!photstats) {
      return <div>No photometry</div>;
    }
    return photstats.peak_mag_global ? (
      <Tooltip title={mjd_to_utc(photstats.peak_mjd_global)}>
        <div>{`${photstats.peak_mag_global.toFixed(4)}`}</div>
      </Tooltip>
    ) : (
      <div>No photometry</div>
    );
  };

  const renderLatestMagnitude = (dataIndex) => {
    const source = sources[dataIndex];
    const photstats = source.photstats[0];
    if (!photstats) {
      return <div>No photometry</div>;
    }
    return photstats.last_detected_mag ? (
      <Tooltip title={mjd_to_utc(photstats.last_detected_mjd)}>
        <div>{`${photstats.last_detected_mag.toFixed(4)}`}</div>
      </Tooltip>
    ) : (
      <div>No photometry</div>
    );
  };

  const renderTNSName = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <div>
        {source.altdata && source.altdata.tns ? source.altdata.tns.name : ""}
      </div>
    );
  };

  const getSavedBy = (source) => {
    // Get the user who saved the source to the specified group
    if (groupID !== undefined) {
      const group = source.groups.find((g) => g.id === groupID);
      return group?.saved_by?.username;
    }
    // Otherwise, get whoever saved it last
    const usernames = source.groups
      .sort((g1, g2) => (g1.saved_at < g2.saved_at ? -1 : 1))
      .map((g) => g.saved_by?.username);
    return usernames[usernames.length - 1];
  };

  const renderSavedBy = (dataIndex) => {
    const source = sources[dataIndex];
    return getSavedBy(source);
  };

  const renderGcnStatus = (dataIndex) => {
    const source = sources[dataIndex];
    let statusIcon = null;
    if (sourcesingcn.filter((s) => s.obj_id === source.id).length === 0) {
      statusIcon = <QuestionMarkIcon size="small" color="primary" />;
    } else if (
      sourcesingcn.filter((s) => s.obj_id === source.id)[0].confirmed === true
    ) {
      statusIcon = <CheckIcon size="small" color="green" />;
    } else if (
      sourcesingcn.filter((s) => s.obj_id === source.id)[0].confirmed === false
    ) {
      statusIcon = <ClearIcon size="small" color="secondary" />;
    }

    return (
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "center",
        }}
        name={`${source.id}_gcn_status`}
      >
        {statusIcon}
        <ConfirmSourceInGCN
          dateobs={gcnEvent.dateobs}
          localization_name={localization.localization_name}
          localization_cumprob={sourceInGcnFilter.localizationCumprob}
          source_id={source.id}
          start_date={sourceInGcnFilter.startDate}
          end_date={sourceInGcnFilter.endDate}
          sources_id_list={sources.map((s) => s.id)}
        />
      </div>
    );
  };

  const handleFilterSubmit = async (formData) => {
    setQueryInProgress(true);

    // Remove empty position
    if (
      formData.position.ra === "" &&
      formData.position.dec === "" &&
      formData.position.radius === ""
    ) {
      delete formData.position;
    }

    const data = filterOutEmptyValues(formData);
    setTableFilterList(
      Object.entries(data).map(([key, value]) => {
        if (key === "position") {
          return `position: ${value.ra} (RA), ${value.dec} (Dec), ${value.radius} (Radius)`;
        }
        return `${key}: ${value}`;
      })
    );

    // Expand cone search params
    if ("position" in data) {
      data.ra = data.position.ra;
      data.dec = data.position.dec;
      data.radius = data.position.radius;
      delete data.position;
    }

    setFilterFormData(data);
    paginateCallback(1, rowsPerPage, {}, data);
    setFilterFormSubmitted(true);
  };

  const handleTableFilterChipChange = (column, filterList, type) => {
    setQueryInProgress(true);

    if (type === "chip") {
      const sourceFilterList = filterList[0];
      // Convert chip filter list to filter form data
      const data = {};
      sourceFilterList?.forEach((filterChip) => {
        const [key, value] = filterChip.split(": ");
        if (key === "position") {
          const fields = value.split(/\s*\(\D*\),*\s*/);
          [data.ra, data.dec, data.radius] = fields;
        } else {
          data[key] = value;
        }
      });
      setTableFilterList(sourceFilterList);
      setFilterFormData(data);
      paginateCallback(1, rowsPerPage, {}, data);
    }
  };

  const customFilterDisplay = () =>
    filterFormSubmitted ? (
      <div className={classes.filterAlert}>
        <InfoIcon /> &nbsp; Filters submitted to server!
      </div>
    ) : (
      <SourceTableFilterForm handleFilterSubmit={handleFilterSubmit} />
    );
  const columns = [
    {
      name: "id",
      label: "Source ID",
      options: {
        // Hijack custom filtering for this column to use for the entire form
        filter: true,
        filterType: "custom",
        filterList: tableFilterList,
        filterOptions: {
          // eslint-disable-next-line react/display-name
          display: () => <></>,
        },
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Source ID"),
        customBodyRenderLite: renderObjId,
      },
    },
    {
      name: "favorites",
      label: "Favorites",
      options: {
        display: displayedColumns.includes("Favorites"),
        customBodyRenderLite: renderFavoritesStar,
      },
    },
    {
      name: "alias",
      label: "Alias",
      options: {
        filter: true,
        sort: false,
        display: displayedColumns.includes("Alias"),
        customBodyRenderLite: renderAlias,
      },
    },
    {
      name: "origin",
      label: "Origin",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Origin"),
        customBodyRenderLite: renderOrigin,
      },
    },
    {
      name: "ra",
      label: "RA (deg)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("RA (deg)"),
        customBodyRenderLite: renderRA,
      },
    },
    {
      name: "dec",
      label: "Dec (deg)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Dec (deg)"),
        customBodyRenderLite: renderDec,
      },
    },
    {
      name: "ra",
      label: "RA (hh:mm:ss)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("RA (hh:mm:ss)"),
        customBodyRenderLite: renderRASex,
      },
    },
    {
      name: "dec",
      label: "Dec (dd:mm:ss)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Dec (dd:mm:ss)"),
        customBodyRenderLite: renderDecSex,
      },
    },
    {
      name: "redshift",
      label: "Redshift",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Redshift"),
      },
    },
    {
      name: "classification",
      label: "Classification",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Classification"),
        customBodyRenderLite: renderClassification,
      },
    },
    {
      name: "groups",
      label: "Groups",
      options: {
        filter: false,
        sort: false,
        display: displayedColumns.includes("Groups"),
        customBodyRenderLite: renderGroups,
      },
    },
    {
      name: "saved_at",
      label: "Date Saved",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Date Saved"),
        customBodyRenderLite: renderDateSaved,
      },
    },
    {
      name: "saved_by",
      label: groupID ? "Saved To Group By" : "Last Saved By",
      options: {
        filter: false,
        sort: false,
        display: displayedColumns.includes(
          groupID ? "Saved To Group By" : "Last Saved By"
        ),
        customBodyRenderLite: renderSavedBy,
      },
    },
    {
      name: "Finder",
      options: {
        filter: false,
        sort: false,
        display: displayedColumns.includes("Finder"),
        customBodyRenderLite: renderFinderButton,
      },
    },
    {
      name: "Spectrum?",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderSpectrumExists,
        display: displayedColumns.includes("Spectrum?"),
      },
    },
    {
      name: "Peak Magnitude",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderPeakMagnitude,
        display: displayedColumns.includes("Peak Magnitude"),
      },
    },
    {
      name: "Latest Magnitude",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderLatestMagnitude,
        display: displayedColumns.includes("Latest Magnitude"),
      },
    },

    {
      name: "TNS Name",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderTNSName,
        display: displayedColumns.includes("TNS Name"),
      },
    },
  ];

  if (includeGcnStatus) {
    columns.splice(1, 0, {
      name: "GCN Status",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderGcnStatus,
        display: displayedColumns.includes("GCN Status"),
      },
    });
  }

  const options = {
    draggableColumns: { enabled: true },
    expandableRows: true,
    renderExpandableRow: renderPullOutRow,
    selectableRows: "none",
    sort: true,
    onTableChange: handleTableChange,
    serverSide: true,
    rowsPerPage: numPerPage,
    page: pageNumber - 1,
    rowsPerPageOptions: [10, 25, 50, 75, 100, 200],
    jumpToPage: true,
    pagination: true,
    count: totalMatches,
    filter: true,
    customFilterDialogFooter: customFilterDisplay,
    onFilterChange: handleTableFilterChipChange,
    onFilterDialogOpen: () => setFilterFormSubmitted(false),
    search: false,
    download: true,
    rowsExpanded: openedRows,
    onRowExpansionChange: (_, allRowsExpanded) => {
      setOpenedRows(allRowsExpanded.map((i) => i.dataIndex));
    },
    onDownload: (buildHead, buildBody) => {
      const renderDownloadClassification = (source) => {
        const classifications = [];
        source?.classifications.forEach((x) => {
          classifications.push(x.classification);
        });
        return classifications.join(";");
      };
      const renderDownloadGroups = (source) => {
        const groups = [];
        source?.groups.forEach((x) => {
          groups.push(x.name);
        });
        return groups.join(";");
      };

      const renderDownloadDateSaved = (source) =>
        getDate(source)?.substring(0, 19);

      const renderDownloadAlias = (source) => {
        const alias = source?.alias;
        let alias_str = "";
        if (alias) {
          alias_str = Array.isArray(alias) ? alias.join(";") : alias;
        }
        return alias_str;
      };
      const renderDownloadTNSName = (source) =>
        source?.altdata && source.altdata.tns ? source.altdata.tns.name : "";

      downloadCallback().then((data) => {
        // if there is no data, cancel download
        if (data?.length > 0) {
          const result =
            buildHead([
              {
                name: "id",
                download: true,
              },
              {
                name: "ra [deg]",
                download: true,
              },
              {
                name: "dec [deg]",
                download: true,
              },
              {
                name: "redshift",
                download: true,
              },
              {
                name: "classification",
                download: true,
              },
              {
                name: "groups",
                download: true,
              },
              {
                name: "Date saved",
                download: true,
              },
              {
                name: "Alias",
                download: true,
              },
              {
                name: "Origin",
                download: true,
              },
              {
                name: "TNS Name",
                download: true,
              },
            ]) +
            buildBody(
              data.map((x) => ({
                ...x,
                data: [
                  x.id,
                  x.ra,
                  x.dec,
                  x.redshift,
                  renderDownloadClassification(x),
                  renderDownloadGroups(x),
                  renderDownloadDateSaved(x),
                  renderDownloadAlias(x),
                  x.origin,
                  renderDownloadTNSName(x),
                ],
              }))
            );
          const blob = new Blob([result], {
            type: "text/csv;charset=utf-8;",
          });
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.setAttribute("download", "sources.csv");
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      });
      return false;
    },
  };

  if (sourceStatus === "requested") {
    columns.push({
      name: "Save/Decline",
      options: {
        filter: false,
        customBodyRenderLite: renderSaveIgnore,
      },
    });
  }

  return (
    <div className={classes.source} data-testid={`source_table_${title}`}>
      <div>
        <Grid
          container
          direction="column"
          alignItems="flex-start"
          justifyContent="flex-start"
          spacing={3}
        >
          {queryInProgress ? (
            <Grid item>
              <CircularProgress />
            </Grid>
          ) : (
            <Grid item className={classes.tableGrid}>
              <StyledEngineProvider injectFirst>
                <ThemeProvider theme={getMuiTheme(theme)}>
                  <MUIDataTable
                    title={!hideTitle ? title : ""}
                    columns={columns}
                    data={sources}
                    options={options}
                  />
                </ThemeProvider>
              </StyledEngineProvider>
            </Grid>
          )}
        </Grid>
      </div>
    </div>
  );
};

SourceTable.propTypes = {
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      ra: PropTypes.number,
      dec: PropTypes.number,
      origin: PropTypes.string,
      alias: PropTypes.arrayOf(PropTypes.string),
      redshift: PropTypes.number,
      classifications: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          classification: PropTypes.string,
          created_at: PropTypes.string,
          groups: PropTypes.arrayOf(
            PropTypes.shape({
              id: PropTypes.number,
              name: PropTypes.string,
            })
          ),
        })
      ),
      altdata: PropTypes.shape({
        tns: PropTypes.shape({
          name: PropTypes.string,
        }),
      }),
      spectrum_exists: PropTypes.bool,
      last_detected_at: PropTypes.string,
      last_detected_mag: PropTypes.number,
      peak_detected_at: PropTypes.string,
      peak_detected_mag: PropTypes.number,
      groups: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          name: PropTypes.string,
        })
      ),
      photstats: PropTypes.arrayOf(
        PropTypes.shape({
          peak_mag_global: PropTypes.number,
          peak_mjd_global: PropTypes.number,
          last_detected_mag: PropTypes.number,
          last_detected_mjd: PropTypes.number,
        })
      ),
    })
  ).isRequired,
  sourceStatus: PropTypes.string,
  groupID: PropTypes.number,
  title: PropTypes.string,
  paginateCallback: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  sortingCallback: PropTypes.func,
  favoritesRemoveButton: PropTypes.bool,
  hideTitle: PropTypes.bool,
  downloadCallback: PropTypes.func.isRequired,
  includeGcnStatus: PropTypes.bool,
  sourceInGcnFilter: PropTypes.shape({
    startDate: PropTypes.string,
    endDate: PropTypes.string,
    localizationCumprob: PropTypes.number,
  }),
};

SourceTable.defaultProps = {
  sourceStatus: "saved",
  groupID: undefined,
  title: "",
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
  sortingCallback: null,
  favoritesRemoveButton: false,
  hideTitle: false,
  includeGcnStatus: false,
  sourceInGcnFilter: {},
};

export default SourceTable;
