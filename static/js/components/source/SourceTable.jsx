import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { Controller, useForm } from "react-hook-form";

import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";
import IconButton from "@mui/material/IconButton";
import FormControlLabel from "@mui/material/FormControlLabel";
import Grid from "@mui/material/Grid";
import AddIcon from "@mui/icons-material/Add";
import Chip from "@mui/material/Chip";
import DeleteIcon from "@mui/icons-material/Delete";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import ThumbUp from "@mui/icons-material/ThumbUp";
import ThumbDown from "@mui/icons-material/ThumbDown";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import MUIDataTable from "mui-datatables";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import Checkbox from "@mui/material/Checkbox";
import CheckIcon from "@mui/icons-material/Check";
import ClearIcon from "@mui/icons-material/Clear";
import InfoIcon from "@mui/icons-material/Info";
import QuestionMarkIcon from "@mui/icons-material/QuestionMark";
import PriorityHigh from "@mui/icons-material/PriorityHigh";
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
import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import DisplayPhotStats from "./DisplayPhotStats";

import { dec_to_dms, mjd_to_utc, ra_to_hours } from "../../units";
import ThumbnailList from "../thumbnail/ThumbnailList";
import ShowClassification from "../classification/ShowClassification";
import ShowSummaries from "../summary/ShowSummaries";
import ShowSummaryHistory from "../summary/ShowSummaryHistory";
import SourceTableFilterForm from "./SourceTableFilterForm";
import StartBotSummary from "../StartBotSummary";
import VegaPhotometry from "../plot/VegaPhotometry";
import FavoritesButton from "../listing/FavoritesButton";
import MultipleClassificationsForm from "../classification/MultipleClassificationsForm";
import UpdateSourceSummary from "./UpdateSourceSummary";
import * as sourceActions from "../../ducks/source";
import * as sourcesActions from "../../ducks/sources";
import * as sourcesingcnActions from "../../ducks/sourcesingcn";
import * as objectTagsActions from "../../ducks/objectTags";
import { getContrastColor } from "../ObjectTags";
import { filterOutEmptyValues } from "../../API";
import { getAnnotationValueString } from "../candidate/ScanningPageCandidateAnnotations";
import ConfirmSourceInGCN from "./ConfirmSourceInGCN";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewSource from "./NewSource";

const VegaSpectrum = React.lazy(() => import("../plot/VegaSpectrum"));
const VegaHR = React.lazy(() => import("../plot/VegaHR"));

const useStyles = makeStyles((theme) => ({
  tableGrid: {
    width: "100%",
  },
  objId: {
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
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
  classificationDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  classificationDeleteDisabled: {
    opacity: 0,
  },
  widgetIcon: {
    display: "none",
  },
  groupChips: {
    display: "flex",
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: "0.25rem",
    maxWidth: "120px",
  },
}));

const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUITableCell: {
        styleOverrides: {
          paddingCheckbox: {
            padding: 0,
            margin: 0,
          },
        },
      },
      MUIDataTableBodyCell: {
        styleOverrides: {
          root: {
            padding: "0.5rem",
            paddingLeft: 0,
            margin: 0,
          },
        },
      },
      MUIDataTableHeadCell: {
        styleOverrides: {
          root: {
            padding: "0.5rem",
            paddingLeft: 0,
            margin: 0,
          },
          sortLabelRoot: {
            height: "1.4rem",
          },
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
  });

let defaultDisplayedColumns = [
  "Source ID",
  "TNS",
  "Favorites",
  "RA (deg)",
  "Dec (deg)",
  "Redshift",
  "Tags",
  "Classification",
  " ",
  "Groups",
  "Saved at",
  "Finder",
];

const RenderShowClassification = ({ source }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const groupUsers = useSelector((state) => state.group?.group_users);
  const currentGroupUser = groupUsers?.filter(
    (groupUser) => groupUser.user_id === currentUser.id,
  )[0];

  useEffect(() => {
    if (
      currentGroupUser?.admin !== undefined &&
      currentGroupUser?.admin !== null
    ) {
      window.localStorage.setItem(
        "CURRENT_GROUP_ADMIN",
        JSON.stringify(currentGroupUser.admin),
      );
    }
  }, [currentGroupUser]);

  const isGroupAdmin = JSON.parse(
    window.localStorage.getItem("CURRENT_GROUP_ADMIN"),
  );

  const { taxonomyList } = useSelector((state) => state.taxonomies);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [classificationSourceToDelete, setClassificationSourceToDelete] =
    useState(null);
  const openDialog = () => {
    setDialogOpen(true);
    setClassificationSourceToDelete(source.id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setClassificationSourceToDelete(null);
  };

  const deleteClassifications = () => {
    dispatch(
      sourceActions.deleteClassifications(classificationSourceToDelete),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Classification deleted"));
        closeDialog();
      }
    });
  };

  const addVotes = (vote) => {
    let success = true;
    source.classifications?.forEach((c) => {
      dispatch(sourceActions.addClassificationVote(c.id, { vote })).then(
        (result) => {
          if (result.status !== "success") {
            success = false;
          }
        },
      );
    });
    if (success) {
      dispatch(showNotification("Votes registered"));
    }
  };

  let upvoteColor = "disabled";
  let downvoteColor = "disabled";
  let upvoteValue = 1;
  let downvoteValue = -1;
  const upvoterIds = [];
  const downvoterIds = [];

  source.classifications?.forEach((classification) => {
    classification.votes?.forEach((s) => {
      if (s.voter_id === currentUser.id) {
        if (s.vote === 1) {
          upvoterIds.push(classification.id);
        } else if (s.vote === -1) {
          downvoterIds.push(classification.id);
        }
      }
    });
  });

  if (source.classifications?.length === upvoterIds.length) {
    upvoteColor = "success";
    upvoteValue = 0;
  } else if (source.classifications?.length === downvoterIds.length) {
    downvoteColor = "error";
    downvoteValue = 0;
  }

  const permission =
    currentUser.permissions.includes("System admin") ||
    currentUser.permissions.includes("Manage groups") ||
    isGroupAdmin;

  return (
    <div>
      <Tooltip
        key={`${source.id}`}
        placement="top-end"
        disableFocusListener
        disableTouchListener
        title={
          <>
            <br />
            <b>All Classifications:</b>
            <br />
            <Button
              key={source.id}
              id="delete_classifications"
              classes={{
                root: classes.classificationDelete,
                disabled: classes.classificationDeleteDisabled,
              }}
              onClick={() => openDialog(source.id)}
              disabled={!permission}
            >
              <DeleteIcon />
            </Button>
            <ConfirmDeletionDialog
              deleteFunction={deleteClassifications}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="classifications"
            />
            <div>
              <Button
                key={source.id}
                id="down_vote"
                onClick={() => addVotes(downvoteValue)}
              >
                <ThumbDown color={downvoteColor} />
              </Button>
            </div>
            <div>
              <Button
                key={source.id}
                id="up_vote"
                onClick={() => addVotes(upvoteValue)}
              >
                <ThumbUp color={upvoteColor} />
              </Button>
            </div>
          </>
        }
      >
        <div>
          <ShowClassification
            classifications={source.classifications}
            taxonomyList={taxonomyList}
            shortened
            fontSize="0.95rem"
          />
        </div>
      </Tooltip>
    </div>
  );
};

RenderShowClassification.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    ra: PropTypes.number,
    dec: PropTypes.number,
    gal_lon: PropTypes.number,
    gal_lat: PropTypes.number,
    origin: PropTypes.string,
    alias: PropTypes.arrayOf(PropTypes.string),
    redshift: PropTypes.number,
    mpc_name: PropTypes.string,
    annotations: PropTypes.arrayOf(
      PropTypes.shape({
        origin: PropTypes.string.isRequired,
        data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
        author: PropTypes.shape({
          username: PropTypes.string.isRequired,
        }),
        created_at: PropTypes.string.isRequired,
      }),
    ).isRequired,
    classifications: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        classification: PropTypes.string,
        created_at: PropTypes.string,
        groups: PropTypes.arrayOf(
          PropTypes.shape({
            id: PropTypes.number,
            name: PropTypes.string,
          }),
        ),
      }),
    ),
    altdata: PropTypes.shape({
      tns: PropTypes.shape({
        name: PropTypes.string,
      }),
    }),
    last_detected_at: PropTypes.string,
    last_detected_mag: PropTypes.number,
    peak_detected_at: PropTypes.string,
    peak_detected_mag: PropTypes.number,
    groups: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
    ),
    photstats: PropTypes.arrayOf(
      PropTypes.shape({
        peak_mag_global: PropTypes.number,
        peak_mjd_global: PropTypes.number,
        last_detected_mag: PropTypes.number,
        last_detected_mjd: PropTypes.number,
      }),
    ),
  }).isRequired,
};

const RenderShowLabelling = ({ source }) => {
  const dispatch = useDispatch();
  const { control } = useForm();
  const [checked, setChecked] = useState(false);

  const currentUser = useSelector((state) => state.profile);

  const labellerUsernames = source.labellers
    ? source.labellers.map((s) => s.username)
    : [];
  const defaultChecked = labellerUsernames.includes(currentUser.username);

  useEffect(() => {
    setChecked(defaultChecked);
  }, [setChecked, defaultChecked]);

  const labelledSource = (check) => {
    const groupIds = [];
    source.groups?.forEach((g) => {
      groupIds.push(g.id);
    });

    if (check === true) {
      dispatch(sourceActions.addSourceLabels(source.id, { groupIds }));
    } else {
      dispatch(sourceActions.deleteSourceLabels(source.id, { groupIds }));
    }
  };

  const checkBox = (event) => {
    setChecked(event.target.checked);
  };

  return (
    <div>
      <FormControlLabel
        key={source.id}
        control={
          <Controller
            render={() => (
              <Checkbox
                onChange={(event) => {
                  checkBox(event);
                  labelledSource(event.target.checked);
                }}
                checked={checked}
                data-testid={`labellingCheckBox${source.id}`}
              />
            )}
            name={`labellingCheckBox${source.id}`}
            control={control}
          />
        }
        label={`Labelled By:  ${labellerUsernames.join(",")}`}
      />
    </div>
  );
};

RenderShowLabelling.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    ra: PropTypes.number,
    dec: PropTypes.number,
    gal_lon: PropTypes.number,
    gal_lat: PropTypes.number,
    origin: PropTypes.string,
    alias: PropTypes.arrayOf(PropTypes.string),
    mpc_name: PropTypes.string,
    redshift: PropTypes.number,
    annotations: PropTypes.arrayOf(
      PropTypes.shape({
        origin: PropTypes.string.isRequired,
        data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
        author: PropTypes.shape({
          username: PropTypes.string.isRequired,
        }).isRequired,
        created_at: PropTypes.string.isRequired,
      }),
    ).isRequired,
    classifications: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        classification: PropTypes.string,
        created_at: PropTypes.string,
        groups: PropTypes.arrayOf(
          PropTypes.shape({
            id: PropTypes.number,
            name: PropTypes.string,
          }),
        ),
      }),
    ),
    altdata: PropTypes.shape({
      tns: PropTypes.shape({
        name: PropTypes.string,
      }),
    }),
    last_detected_at: PropTypes.string,
    last_detected_mag: PropTypes.number,
    peak_detected_at: PropTypes.string,
    peak_detected_mag: PropTypes.number,
    groups: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
    ),
    photstats: PropTypes.arrayOf(
      PropTypes.shape({
        peak_mag_global: PropTypes.number,
        peak_mjd_global: PropTypes.number,
        last_detected_mag: PropTypes.number,
        last_detected_mjd: PropTypes.number,
      }),
    ),
    labellers: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        username: PropTypes.string,
      }),
    ),
  }).isRequired,
};

// MUI data table with pull out rows containing a summary of each source.
// This component is used in GroupSources, SourceList and Favorites page.
const SourceTable = ({
  sources,
  title = "Sources",
  sourceStatus = "saved",
  groupID,
  paginateCallback,
  pageNumber,
  totalMatches,
  numPerPage,
  sortingCallback,
  downloadCallback,
  includeGcnStatus = false,
  sourceInGcnFilter,
  fixedHeader = false,
}) => {
  // sourceStatus should be one of either "saved" (default) or "requested" to add a button to agree to save the source.
  // If groupID is not given, show all data available to user's accessible groups

  const dispatch = useDispatch();
  const { taxonomyList } = useSelector((state) => state.taxonomies);

  const classes = useStyles();
  const theme = useTheme();

  const [searchBy, setSearchBy] = useState("name");
  const [openNew, setOpenNew] = useState(false);

  if (includeGcnStatus) {
    defaultDisplayedColumns.push("GCN Status");
    defaultDisplayedColumns.push("Explanation");
    defaultDisplayedColumns.push("Notes");
    defaultDisplayedColumns.push("Host");
    defaultDisplayedColumns.push("Host Offset (arcsec)");
  }

  const [displayedColumns, setDisplayedColumns] = useState(
    defaultDisplayedColumns,
  );
  const [openedRows, setOpenedRows] = useState([]);

  const [filterFormSubmitted, setFilterFormSubmitted] = useState(false);

  const [tableFilterList, setTableFilterList] = useState([]);
  const [filterFormData, setFilterFormData] = useState(null);

  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);
  const [queryInProgress, setQueryInProgress] = useState(false);

  const gcnEvent = useSelector((state) => state.gcnEvent);

  const sourcesingcn = useSelector((state) => state.sourcesingcn.sourcesingcn);

  const photometry = useSelector((state) => state.photometry);

  const tagOptions = useSelector((state) => state.objectTags || []);

  useEffect(() => {
    dispatch(objectTagsActions.fetchTagOptions());
  }, [dispatch]);

  useEffect(() => {
    if (sources) {
      setQueryInProgress(false);
      if (includeGcnStatus) {
        dispatch(
          sourcesingcnActions.fetchSourcesInGcn(gcnEvent.dateobs, {
            localizationName: sourceInGcnFilter?.localizationName,
            sourcesIdList: sources.map((s) => s.id),
          }),
        );
      }
    }
  }, [sources]);

  useEffect(() => {
    const data = {
      ...filterFormData,
    };
    if (data?.sourceID?.length > 0 && searchBy === "comment") {
      data.commentsFilter = data.sourceID;
      delete data.sourceID;
      paginateCallback(1, rowsPerPage, {}, data);
      setFilterFormData(data);
    } else if (data?.commentsFilter?.length > 0 && searchBy === "name") {
      data.sourceID = data.commentsFilter;
      delete data.commentsFilter;
      paginateCallback(1, rowsPerPage, {}, data);
      setFilterFormData(data);
    }
  }, [searchBy]);

  const handleTableChange = (action, tableState) => {
    switch (action) {
      case "changePage":
      case "changeRowsPerPage":
        setRowsPerPage(tableState.rowsPerPage);
        paginateCallback(
          tableState.page + 1,
          tableState.rowsPerPage,
          tableState.sortOrder,
          filterFormData,
        );
        break;
      case "viewColumnsChange":
        // Save displayed column labels
        setDisplayedColumns(
          tableState.columns
            ?.filter((column) => column.display === "true")
            ?.map((column) => column.label),
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
      sourceActions.acceptSaveRequest({ sourceID, groupID }),
    );
    if (result.status === "success") {
      dispatch(
        sourcesActions.fetchPendingGroupSources({
          group_ids: [groupID],
          pageNumber: 1,
          numPerPage: 10,
        }),
      );
      dispatch(
        sourcesActions.fetchSavedGroupSources({
          group_ids: [groupID],
          pageNumber: 1,
          numPerPage: 10,
        }),
      );
    }
  };

  const handleIgnoreSource = async (sourceID) => {
    const result = await dispatch(
      sourceActions.declineSaveRequest({ sourceID, groupID }),
    );
    if (result.status === "success") {
      dispatch(
        sourcesActions.fetchPendingGroupSources({
          group_ids: [groupID],
          pageNumber: 1,
          numPerPage: 10,
        }),
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
              <VegaPhotometry sourceId={source.id} />
            </Grid>
            <Grid item>
              {photometry[source.id] && photometry[source.id].length > 0 ? (
                <VegaPhotometry
                  sourceId={source.id}
                  annotations={annotations}
                  folded
                />
              ) : null}
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
              <Suspense
                fallback={
                  <div>
                    <CircularProgress color="secondary" />
                  </div>
                }
              >
                <VegaSpectrum
                  sourceId={source.id}
                  width={plotWidth}
                  height={specPlotHeight}
                  legendOrient={legendOrient}
                  normalization="median"
                />
              </Suspense>
            </Grid>
            <Grid item>
              <div className={classes.annotations}>
                {annotations && annotations.length > 0 && (
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
                                        value,
                                      )}`}
                                    />
                                  </ListItem>
                                ),
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
            <Grid item xs={12}>
              <ShowSummaries summaries={source.summary_history} />
              {source.summary_history?.length < 1 ||
              !source.summary_history ||
              source.summary_history[0].summary === null ? (
                <div>
                  <b>Summarize: &nbsp;</b>
                </div>
              ) : null}
              <UpdateSourceSummary source={source} />
              {source.classifications?.length > 0 ? (
                <StartBotSummary obj_id={source.id} />
              ) : null}
              {source.summary_history?.length > 0 ? (
                <ShowSummaryHistory
                  summaries={source.summary_history}
                  obj_id={source.id}
                />
              ) : null}
            </Grid>
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
        target="_blank"
        rel="noopener noreferrer"
      >
        <span className={classes.objId}>{objid}</span>
      </Link>
    );
  };

  const renderTNSName = (dataIndex) => {
    const source = sources[dataIndex];
    if (source.tns_name) {
      return (
        <a
          key={source.tns_name}
          href={`https://www.wis-tns.org/object/${
            source.tns_name.trim().includes(" ")
              ? source.tns_name.split(" ")[1]
              : source.tns_name
          }`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ whiteSpace: "nowrap" }}
        >
          {`${source.tns_name} `}
        </a>
      );
    }
    return null;
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

  const renderGalLon = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_gal_lon`}>{source.gal_lon.toFixed(6)}</div>;
  };

  const renderGalLat = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_gal_lat`}>{source.gal_lat.toFixed(6)}</div>;
  };

  const renderHost = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_host`}>{source.host?.name}</div>;
  };

  const renderHostOffset = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <div key={`${source.id}_host_offset`}>
        {source.host_offset?.toFixed(3)}
      </div>
    );
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
        <div>
          <RenderShowClassification source={source} />
        </div>
      </Suspense>
    );
  };

  const renderPhotStats = (dataIndex) => {
    const source = sources[dataIndex];

    return (
      <Suspense
        fallback={
          <div>
            <CircularProgress color="secondary" />
          </div>
        }
      >
        <div>
          <DisplayPhotStats
            photstats={source.photstats[0]}
            display_header={false}
          />
        </div>
      </Suspense>
    );
  };

  const renderLabelling = (dataIndex) => {
    const source = sources[dataIndex];

    return (
      <Suspense
        fallback={
          <div>
            <CircularProgress color="secondary" />
          </div>
        }
      >
        <div>
          <RenderShowLabelling source={source} />
        </div>
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
      <div key={`${source.id}_groups`} className={classes.groupChips}>
        {getGroups(source).map((group) => (
          <div key={group.name}>
            <Chip
              label={group.name.substring(0, 15)}
              key={group.id}
              size="small"
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
          secondary
          size="small"
          onClick={() => {
            handleSaveSource(source.id);
          }}
          data-testid={`saveSourceButton_${source.id}`}
        >
          Save
        </Button>
        &nbsp;
        <Button
          secondary
          size="small"
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

  const renderMPCName = (dataIndex) => {
    const source = sources[dataIndex];
    return <div>{source.mpc_name ? source.mpc_name : ""}</div>;
  };

  const renderTags = (dataIndex) => {
    const source = sources[dataIndex];
    const tags = source.tags || [];

    if (tags.length === 0) {
      return null;
    }

    const tagsWithColors = tags.map((tag) => {
      const tagOption = tagOptions.find(
        (option) => option.id === tag.objtagoption_id,
      );
      return {
        ...tag,
        color: tagOption?.color || "#dddfe2",
      };
    });

    return (
      <div key={`${source.id}_tags`} className={classes.groupChips}>
        {tagsWithColors.map((tag) => (
          <Chip
            key={tag.id}
            label={tag.name}
            size="small"
            style={{
              backgroundColor: tag.color,
              color: getContrastColor(tag.color),
            }}
          />
        ))}
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
      statusIcon = <PriorityHigh size="small" color="primary" />;
    } else if (
      sourcesingcn.filter((s) => s.obj_id === source.id)[0].confirmed === true
    ) {
      statusIcon = <CheckIcon size="small" color="green" />;
    } else if (
      sourcesingcn.filter((s) => s.obj_id === source.id)[0].confirmed === false
    ) {
      statusIcon = <ClearIcon size="small" color="secondary" />;
    } else {
      statusIcon = <QuestionMarkIcon size="small" color="primary" />;
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
          localization_name={sourceInGcnFilter.localizationName}
          localization_cumprob={sourceInGcnFilter.localizationCumprob}
          source_id={source.id}
          start_date={sourceInGcnFilter.startDate}
          end_date={sourceInGcnFilter.endDate}
          sources_id_list={sources.map((s) => s.id)}
        />
      </div>
    );
  };

  const renderGcnStatusExplanation = (dataIndex) => {
    const source = sources[dataIndex];
    let statusExplanation = null;
    if (sourcesingcn.filter((s) => s.obj_id === source.id).length === 0) {
      statusExplanation = "";
    } else {
      statusExplanation = sourcesingcn.filter((s) => s.obj_id === source.id)[0]
        .explanation;
    }
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "center",
        }}
        name={`${source.id}_gcn_status_explanation`}
      >
        {statusExplanation}
      </div>
    );
  };

  const renderGcnNotes = (dataIndex) => {
    const source = sources[dataIndex];
    let notes = "";
    if (sourcesingcn.filter((s) => s.obj_id === source.id).length) {
      notes = sourcesingcn.filter((s) => s.obj_id === source.id)[0].notes;
    }
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {notes}
      </div>
    );
  };

  const handleSearchChange = (searchText) => {
    const data = {
      ...filterFormData,
    };
    if (searchBy === "name") {
      data.sourceID = searchText;
      delete data.commentsFilter;
    } else if (searchBy === "comment") {
      data.commentsFilter = searchText;
      delete data.sourceID;
    } else {
      dispatch(showNotification("Invalid searchBy parameter", "error"));
    }
    paginateCallback(1, rowsPerPage, {}, data);
    setFilterFormData(data);
  };

  const handleFilterSubmit = async (formData) => {
    setQueryInProgress(true);

    // Remove empty position
    if (
      !formData.position.ra &&
      !formData.position.dec &&
      !formData.position.radius
    ) {
      delete formData.position;
    }

    const data = filterOutEmptyValues(formData);

    // the method above drops any empty or false params, but we make sure to keep requireDetections
    // if it is False, as it's default is to be True
    if (formData.requireDetections === false) {
      data.requireDetections = false;
    }

    setTableFilterList(
      Object.entries(data).map(([key, value]) => {
        if (key === "position") {
          return `position: ${value.ra} (RA), ${value.dec} (Dec), ${value.radius} (Radius)`;
        }
        return `${key}: ${value}`;
      }),
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
          [data.ra, data.dec, data.radius] = value.split(/\s*\(\D*\),*\s*/);
        } else {
          data[key] = value;
        }
      });

      dispatch(sourcesActions.fetchSources(data)).then((response) => {
        if (response.status === "success") {
          setTableFilterList(sourceFilterList);
          setFilterFormData(data);
        } else {
          setTableFilterList([]);
          setFilterFormData([]);
        }
      });
      paginateCallback(1, rowsPerPage, {}, data);
    }
  };

  const handleClose = () => {
    setOpenNew(false);
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
          display: () => <></>,
        },
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Source ID"),
        customBodyRenderLite: renderObjId,
      },
    },
    {
      name: "TNS",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderTNSName,
        display: displayedColumns.includes("TNS"),
      },
    },
    {
      name: "alias",
      label: "Alias",
      options: {
        filter: true,
        sort: true,
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
      name: "l",
      label: "l (deg)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("l (deg)"),
        customBodyRenderLite: renderGalLon,
      },
    },
    {
      name: "b",
      label: "b (deg)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("b (deg)"),
        customBodyRenderLite: renderGalLat,
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
      name: "tags",
      label: "Tags",
      options: {
        filter: false,
        sort: false,
        display: displayedColumns.includes("Tags"),
        customBodyRenderLite: renderTags,
        setCellProps: () => ({ style: { maxWidth: "min(150px, 20vw)" } }),
      },
    },
    {
      name: "classification",
      label: "Classification",
      options: {
        filter: false,
        sort: false,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Classification"),
        customBodyRenderLite: renderClassification,
        setCellProps: () => ({ style: { maxWidth: "min(150px, 20vw)" } }),
      },
    },
    {
      name: "host",
      label: "Host",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Host"),
        customBodyRenderLite: renderHost,
      },
    },
    {
      name: "host_offset",
      label: "Host Offset (arcsec)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Host Offset (arcsec)"),
        customBodyRenderLite: renderHostOffset,
      },
    },
    {
      name: "photstats",
      label: " ",
      options: {
        filter: false,
        sort: false,
        sortThirdClickReset: true,
        display: displayedColumns.includes(" "),
        customBodyRenderLite: renderPhotStats,
        setCellProps: () => ({ style: { maxWidth: "5rem" } }),
      },
    },
    {
      name: "labelling",
      label: "Labelling",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Labelling"),
        customBodyRenderLite: renderLabelling,
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
      label: "Saved at",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        display: displayedColumns.includes("Saved at"),
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
          groupID ? "Saved To Group By" : "Last Saved By",
        ),
        customBodyRenderLite: renderSavedBy,
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
      name: "MPC Name",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderMPCName,
        display: displayedColumns.includes("MPC Name"),
      },
    },
    {
      name: "favorites",
      label: " ",
      options: {
        display: displayedColumns.includes("Favorites"),
        customBodyRenderLite: renderFavoritesStar,
        setCellProps: () => ({ style: { maxWidth: "5rem" } }),
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
  ];

  if (includeGcnStatus) {
    columns.splice(10, 0, {
      name: "gcn_status",
      label: "GCN Status",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderGcnStatus,
        display: displayedColumns.includes("GCN Status"),
      },
    });
    columns.splice(11, 0, {
      name: "gcn_explanation",
      label: "Explanation",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderGcnStatusExplanation,
        display: displayedColumns.includes("Explanation"),
      },
    });
    columns.splice(12, 0, {
      name: "gcn_notes",
      label: "Notes",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderGcnNotes,
        display: displayedColumns.includes("Notes"),
      },
    });
  }

  const options = {
    ...(fixedHeader
      ? { fixedHeader: true, tableBodyHeight: "calc(100vh - 201px)" }
      : {}),
    draggableColumns: { enabled: true },
    expandableRows: true,
    renderExpandableRow: renderPullOutRow,
    selectableRows: "none",
    sort: true,
    onTableChange: handleTableChange,
    serverSide: true,
    rowsPerPage: numPerPage,
    page: pageNumber - 1,
    rowsPerPageOptions: [1, 5, 10, 25, 50, 75, 100, 200],
    jumpToPage: true,
    pagination: true,
    count: totalMatches,
    filter: true,
    customFilterDialogFooter: customFilterDisplay,
    onFilterChange: handleTableFilterChipChange,
    onFilterDialogOpen: () => setFilterFormSubmitted(false),
    search: true,
    onSearchChange: handleSearchChange,
    download: downloadCallback !== null && downloadCallback !== undefined,
    customToolbar: () => (
      <>
        <Select
          label="Search by"
          variant="standard"
          value={searchBy}
          onChange={(event) => {
            setSearchBy(event.target.value);
          }}
          style={{ marginLeft: "10px" }}
          size="small"
        >
          <MenuItem value="name">ID/IAU</MenuItem>
          <MenuItem value="comment">Comment</MenuItem>
        </Select>
        <IconButton
          name="new_source"
          onClick={() => {
            setOpenNew(true);
          }}
        >
          <AddIcon />
        </IconButton>
      </>
    ),
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
      const renderDownloadProbability = (source) => {
        const probabilities = [];
        source?.classifications.forEach((x) => {
          probabilities.push(x.probability);
        });
        return probabilities.join(";");
      };
      const renderDownloadAnnotationKey = (source) => {
        const annotationKeys = [];
        source?.annotations.forEach((x) => {
          Object.entries(x.data).forEach((keyValuePair) => {
            annotationKeys.push(keyValuePair[0]);
          });
        });
        return annotationKeys.join(";");
      };
      const renderDownloadAnnotationOrigin = (source) => {
        const annotationOrigins = [];
        source?.annotations.forEach((x) => {
          annotationOrigins.push(x.origin);
        });
        return annotationOrigins.join(";");
      };
      const renderDownloadAnnotationOriginKeyValuePairCount = (source) => {
        const annotationOriginsKeyValuePairCount = [];
        source?.annotations.forEach((x) => {
          annotationOriginsKeyValuePairCount.push(
            Object.entries(x.data).length,
          );
        });
        return annotationOriginsKeyValuePairCount.join(";");
      };
      const renderDownloadAnnotationValue = (source) => {
        const annotationValues = [];
        source?.annotations.forEach((x) => {
          Object.entries(x.data).forEach((keyValuePair) => {
            annotationValues.push(keyValuePair[1]);
          });
        });
        return annotationValues.join(";");
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
        source?.tns_name ? source.tns_name : "";

      downloadCallback().then((data) => {
        // if there is no data, cancel download
        if (data?.length > 0) {
          const head = [
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
              name: "probability",
              download: true,
            },
            {
              name: "annotation origin",
              download: true,
            },
            {
              name: "annotation origin key-value pair count",
              download: true,
            },
            {
              name: "annotation key",
              download: true,
            },
            {
              name: "annotation value",
              download: true,
            },
            {
              name: "groups",
              download: true,
            },
            {
              name: "Saved at",
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
              name: "TNS",
              download: true,
            },
          ];
          if (includeGcnStatus) {
            head.push({
              name: "GCN Status",
              download: true,
            });
            head.push({
              name: "Explanation",
              download: true,
            });
            head.push({
              name: "Notes",
              download: true,
            });
          }

          const formatDataFunc = (x) => {
            const formattedData = [
              x.id,
              x.ra,
              x.dec,
              x.redshift,
              renderDownloadClassification(x),
              renderDownloadProbability(x),
              renderDownloadAnnotationOrigin(x),
              renderDownloadAnnotationOriginKeyValuePairCount(x),
              renderDownloadAnnotationKey(x),
              renderDownloadAnnotationValue(x),
              renderDownloadGroups(x),
              renderDownloadDateSaved(x),
              renderDownloadAlias(x),
              x.origin,
              renderDownloadTNSName(x),
            ];
            if (includeGcnStatus) {
              formattedData.push(x.gcn ? x.gcn.status : "");
              formattedData.push(x.gcn ? x.gcn.explanation : "");
              formattedData.push(x.gcn ? x.gcn.notes : "");
            }
            return formattedData;
          };

          const result =
            buildHead(head) +
            buildBody(
              data.map((x) => ({
                ...x,
                data: formatDataFunc(x),
              })),
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
                    title={title}
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
      <div>
        {openNew && (
          <Dialog open={openNew} onClose={handleClose} maxWidth="md">
            <DialogContent dividers>
              <NewSource classes={classes} />
            </DialogContent>
          </Dialog>
        )}
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
      gal_lon: PropTypes.number,
      gal_lat: PropTypes.number,
      origin: PropTypes.string,
      host: PropTypes.shape({
        catalog_name: PropTypes.string,
        name: PropTypes.string,
        alt_name: PropTypes.string,
        ra: PropTypes.number,
        dec: PropTypes.number,
        distmpc: PropTypes.number,
        distmpc_unc: PropTypes.number,
        redshift: PropTypes.number,
        redshift_error: PropTypes.number,
        sfr_fuv: PropTypes.number,
        mstar: PropTypes.number,
        magb: PropTypes.number,
        magk: PropTypes.number,
        a: PropTypes.number,
        b2a: PropTypes.number,
        pa: PropTypes.number,
        btc: PropTypes.number,
      }),
      host_offset: PropTypes.number,
      alias: PropTypes.arrayOf(PropTypes.string),
      tns_name: PropTypes.string,
      mpc_name: PropTypes.string,
      redshift: PropTypes.number,
      annotations: PropTypes.arrayOf(
        PropTypes.shape({
          origin: PropTypes.string.isRequired,
          data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
          author: PropTypes.shape({
            username: PropTypes.string.isRequired,
          }),
          created_at: PropTypes.string.isRequired,
        }),
      ).isRequired,
      classifications: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          classification: PropTypes.string,
          created_at: PropTypes.string,
          groups: PropTypes.arrayOf(
            PropTypes.shape({
              id: PropTypes.number,
              name: PropTypes.string,
            }),
          ),
        }),
      ),
      altdata: PropTypes.shape({
        tns: PropTypes.shape({
          name: PropTypes.string,
        }),
      }),
      last_detected_at: PropTypes.string,
      last_detected_mag: PropTypes.number,
      peak_detected_at: PropTypes.string,
      peak_detected_mag: PropTypes.number,
      groups: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          name: PropTypes.string,
        }),
      ),
      photstats: PropTypes.arrayOf(
        PropTypes.shape({
          peak_mag_global: PropTypes.number,
          peak_mjd_global: PropTypes.number,
          last_detected_mag: PropTypes.number,
          last_detected_mjd: PropTypes.number,
        }),
      ),
      tags: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number.isRequired,
          name: PropTypes.string.isRequired,
          objtagoption_id: PropTypes.number,
        }),
      ),
    }),
  ).isRequired,
  sourceStatus: PropTypes.string,
  groupID: PropTypes.number,
  title: PropTypes.string,
  paginateCallback: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  sortingCallback: PropTypes.func,
  downloadCallback: PropTypes.func,
  includeGcnStatus: PropTypes.bool,
  sourceInGcnFilter: PropTypes.shape({
    startDate: PropTypes.string,
    endDate: PropTypes.string,
    localizationName: PropTypes.string,
    localizationCumprob: PropTypes.number,
  }),
  fixedHeader: PropTypes.bool,
};

SourceTable.defaultProps = {
  sourceStatus: "saved",
  groupID: undefined,
  title: "Sources",
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
  sortingCallback: null,
  downloadCallback: null,
  includeGcnStatus: false,
  sourceInGcnFilter: {},
  fixedHeader: false,
};

export default SourceTable;
