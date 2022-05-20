import React, { useEffect, Suspense, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import {
  makeStyles,
  createTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";
import useMediaQuery from "@material-ui/core/useMediaQuery";
import Button from "@material-ui/core/Button";
import IconButton from "@material-ui/core/IconButton";
import OpenInNewIcon from "@material-ui/icons/OpenInNew";
import ArrowUpward from "@material-ui/icons/ArrowUpward";
import ArrowDownward from "@material-ui/icons/ArrowDownward";
import SortIcon from "@material-ui/icons/Sort";
import Chip from "@material-ui/core/Chip";
import Box from "@material-ui/core/Box";
import Tooltip from "@material-ui/core/Tooltip";
import Popover from "@material-ui/core/Popover";
import HelpOutlineIcon from "@material-ui/icons/HelpOutline";
import Form from "@rjsf/material-ui";
import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import * as candidatesActions from "../ducks/candidates";
import ThumbnailList from "./ThumbnailList";
import SaveCandidateButton from "./SaveCandidateButton";
import FilterCandidateList from "./FilterCandidateList";
import ScanningPageCandidateAnnotations, {
  getAnnotationValueString,
} from "./ScanningPageCandidateAnnotations";
import EditSourceGroups from "./EditSourceGroups";
import { ra_to_hours, dec_to_dms } from "../units";
import RejectButton from "./RejectButton";
import VegaPhotometry from "./VegaPhotometry";
import Spinner from "./Spinner";
import AddClassificationsScanningPage from "./AddClassificationsScanningPage";

const useStyles = makeStyles((theme) => ({
  candidateListContainer: {
    padding: "1rem",
  },
  table: {
    marginTop: "1rem",
  },
  title: {
    marginBottom: "0.625rem",
  },
  pages: {
    margin: "1rem",
    "& > div": {
      display: "inline-block",
      margin: "1rem",
    },
  },
  spinnerDiv: {
    paddingTop: "2rem",
  },
  itemPaddingBottom: {
    paddingBottom: "0.1rem",
  },
  infoItem: {
    display: "flex",
    "& > span": {
      paddingLeft: "0.25rem",
      paddingBottom: "0.1rem",
    },
    flexFlow: "row wrap",
  },
  infoItemPadded: {
    "& > span": {
      paddingLeft: "0.25rem",
      paddingBottom: "0.1rem",
    },
  },
  saveCandidateButton: {
    margin: "0.5rem 0",
  },
  thumbnails: (props) => ({
    minWidth: props.thumbnailsMinWidth,
  }),
  info: (props) => ({
    fontSize: "0.875rem",
    minWidth: props.infoMinWidth,
    maxWidth: props.infoMaxWidth,
  }),
  annotations: (props) => ({
    minWidth: props.annotationsMinWidth,
    maxWidth: props.annotationsMaxWidth,
    overflowWrap: "break-word",
  }),
  sortButtton: {
    verticalAlign: "top",
    "&:hover": {
      color: theme.palette.primary.main,
    },
  },
  chip: {
    margin: theme.spacing(0.5),
  },
  typography: {
    padding: theme.spacing(2),
  },
  helpButton: {
    display: "inline-block",
  },
  position: {
    fontWeight: "bold",
    fontSize: "110%",
  },
  formControl: {
    margin: theme.spacing(1),
    minWidth: 120,
  },
  formContainer: {
    display: "flex",
    flexFlow: "row wrap",
    alignItems: "center",
  },
  idButton: {
    textTransform: "none",
    marginBottom: theme.spacing(1),
  },
}));

// Tweak responsive column widths
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    overrides: {
      MUIDataTableBodyCell: {
        root: {
          padding: `${theme.spacing(1)}px ${theme.spacing(
            0.5
          )}px ${theme.spacing(1)}px ${theme.spacing(1)}px`,
        },
        stackedHeader: {
          verticalAlign: "top",
        },
        stackedCommon: {
          [theme.breakpoints.up("xs")]: { width: "calc(100%)" },
          "&$stackedHeader": {
            display: "none",
            overflowWrap: "break-word",
          },
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
            maxWidth: "25%",
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
      MUIDataTableFilter: {
        root: {
          maxHeight: "calc(100vh - 5rem)",
        },
      },
      MUIDataTableFilterList: {
        chip: {
          maxWidth: "100%",
        },
      },
    },
  });

const getMostRecentClassification = (classifications) => {
  // Display the most recent non-zero probability class
  const filteredClasses = classifications?.filter((i) => i.probability > 0);
  const sortedClasses = filteredClasses?.sort((a, b) =>
    a.modified < b.modified ? 1 : -1
  );
  const recentClassification =
    sortedClasses?.length > 0 ? `${sortedClasses[0].classification}` : null;

  return recentClassification;
};

const getMuiPopoverTheme = () =>
  createTheme({
    overrides: {
      MuiPopover: {
        paper: {
          maxWidth: "30rem",
        },
      },
    },
  });

const defaultNumPerPage = 25;

const CustomSortToolbar = ({
  selectedAnnotationSortOptions,
  rowsPerPage,
  filterGroups,
  filterFormData,
  setQueryInProgress,
  loaded,
  sortOrder,
  setSortOrder,
}) => {
  const classes = useStyles();

  const dispatch = useDispatch();
  const handleSort = async () => {
    const newSortOrder =
      sortOrder === null || sortOrder === "desc" ? "asc" : "desc";
    setSortOrder(newSortOrder);

    setQueryInProgress(true);
    let data = {
      pageNumber: 1,
      numPerPage: rowsPerPage,
      groupIDs: filterGroups?.map((g) => g.id).join(),
      sortByAnnotationOrigin: selectedAnnotationSortOptions.origin,
      sortByAnnotationKey: selectedAnnotationSortOptions.key,
      sortByAnnotationOrder: newSortOrder,
    };
    if (filterFormData !== null) {
      data = {
        ...data,
        ...filterFormData,
      };
    }

    await dispatch(
      candidatesActions.setCandidatesAnnotationSortOptions({
        ...selectedAnnotationSortOptions,
        order: newSortOrder,
      })
    );
    await dispatch(candidatesActions.fetchCandidates(data));
    setQueryInProgress(false);
  };

  // Wait until sorted data is received before rendering the toolbar
  return loaded ? (
    <Tooltip title="Sort on Selected Annotation">
      <span>
        <IconButton
          onClick={handleSort}
          disabled={selectedAnnotationSortOptions === null}
          className={classes.sortButtton}
          data-testid="sortOnAnnotationButton"
        >
          <span>
            <SortIcon />
            {sortOrder !== null && sortOrder === "asc" && <ArrowUpward />}
            {sortOrder !== null && sortOrder === "desc" && <ArrowDownward />}
          </span>
        </IconButton>
      </span>
    </Tooltip>
  ) : (
    <span />
  );
};

CustomSortToolbar.propTypes = {
  selectedAnnotationSortOptions: PropTypes.shape({
    origin: PropTypes.string.isRequired,
    key: PropTypes.string.isRequired,
    order: PropTypes.string,
  }),
  setQueryInProgress: PropTypes.func.isRequired,
  rowsPerPage: PropTypes.number.isRequired,
  filterGroups: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
  filterFormData: PropTypes.shape({}),
  loaded: PropTypes.bool.isRequired,
  sortOrder: PropTypes.string,
  setSortOrder: PropTypes.func.isRequired,
};

CustomSortToolbar.defaultProps = {
  selectedAnnotationSortOptions: null,
  filterFormData: null,
  sortOrder: null,
};

const columnNames = ["Images", "Info", "Photometry", "Autoannotations"];

const CandidateList = () => {
  const [queryInProgress, setQueryInProgress] = useState(false);
  const [rowsPerPage, setRowsPerPage] = useState(defaultNumPerPage);
  const [filterGroups, setFilterGroups] = useState([]);
  const [viewColumns, setViewColumns] = useState(columnNames);
  // Maintain the three thumbnails in a row for larger screens
  const largeScreen = useMediaQuery((theme) => theme.breakpoints.up("md"));
  const thumbnailsMinWidth = largeScreen ? "30rem" : 0;
  const infoMinWidth = largeScreen ? "7rem" : 0;
  const infoMaxWidth = "14rem";
  const annotationsMinWidth = largeScreen ? "10rem" : 0;
  const annotationsMaxWidth = "25rem";
  const classes = useStyles({
    thumbnailsMinWidth,
    infoMinWidth,
    infoMaxWidth,
    annotationsMinWidth,
    annotationsMaxWidth,
  });
  const theme = useTheme();
  const {
    candidates,
    pageNumber,
    totalMatches,
    queryID,
    selectedAnnotationSortOptions,
  } = useSelector((state) => state.candidates);

  const [sortOrder, setSortOrder] = useState(
    selectedAnnotationSortOptions ? selectedAnnotationSortOptions.order : null
  );

  const { scanningProfiles } = useSelector(
    (state) => state.profile.preferences
  );

  const defaultScanningProfile = scanningProfiles?.find(
    (profile) => profile.default
  );

  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible
  );
  const allGroups = (useSelector((state) => state.groups.all) || []).filter(
    (g) => !g.single_user_group
  );

  const availableAnnotationsInfo = useSelector(
    (state) => state.candidates.annotationsInfo
  );

  const filterFormData = useSelector(
    (state) => state.candidates.filterFormData
  );

  const dispatch = useDispatch();

  useEffect(() => {
    // Grab the available annotation fields for filtering
    dispatch(candidatesActions.fetchAnnotationsInfo());
  }, [dispatch]);

  useEffect(() => {
    if (defaultScanningProfile?.sortingOrder) {
      dispatch(
        candidatesActions.setCandidatesAnnotationSortOptions({
          origin: defaultScanningProfile.sortingOrigin,
          key: defaultScanningProfile.sortingKey,
          order: defaultScanningProfile.sortingOrder,
        })
      );
      setSortOrder(defaultScanningProfile.sortingOrder);
    }
  }, [dispatch, defaultScanningProfile]);

  const [annotationsHeaderAnchor, setAnnotationsHeaderAnchor] = useState(null);
  const annotationsHelpOpen = Boolean(annotationsHeaderAnchor);
  const annotationsHelpId = annotationsHelpOpen ? "simple-popover" : undefined;
  const handleClickAnnotationsHelp = (event) => {
    setAnnotationsHeaderAnchor(event.currentTarget);
  };
  const handleCloseAnnotationsHelp = () => {
    setAnnotationsHeaderAnchor(null);
  };

  const candidateHasAnnotationWithSelectedKey = (candidateObj) => {
    const annotation = candidateObj.annotations.find(
      (a) => a.origin === selectedAnnotationSortOptions.origin
    );
    if (annotation === undefined) {
      return false;
    }
    return selectedAnnotationSortOptions.key in annotation.data;
  };

  const getCandidateSelectedAnnotationValue = (candidateObj) => {
    const annotation = candidateObj.annotations.find(
      (a) => a.origin === selectedAnnotationSortOptions.origin
    );
    return getAnnotationValueString(
      annotation.data[selectedAnnotationSortOptions.key]
    );
  };

  // Annotations filtering
  const [tableFilterList, setTableFilterList] = useState([]);
  const [filterListQueryStrings, setFilterListQueryStrings] = useState([]);

  const filterChipToAnnotationObj = (chip) => {
    // Convert a MuiDataTable filter list chip-formatted string to an object.
    // Returns null for improperly formatted strings
    const tokens = chip.split(/\s\(|\):|-/);
    let returnObject = null;
    switch (tokens.length) {
      case 3:
        returnObject = {
          origin: tokens[1].trim(),
          key: tokens[0].trim(),
          value: tokens[2].trim(),
        };
        break;
      case 4:
        returnObject = {
          origin: tokens[1].trim(),
          key: tokens[0].trim(),
          min: tokens[2].trim(),
          max: tokens[3].trim(),
        };
        break;
      default:
        break;
    }
    return returnObject;
  };

  const filterAnnotationObjToChip = (annotationObj) =>
    // Convert an object representing an annotation filter to a formatted string
    // to be displayed by the MuiDataTable
    "value" in annotationObj
      ? `${annotationObj.key} (${annotationObj.origin}): ${annotationObj.value}`
      : `${annotationObj.key} (${annotationObj.origin}): ${annotationObj.min} - ${annotationObj.max}`;

  const handleFilterSubmit = async (filterListQueryString) => {
    setQueryInProgress(true);

    let data = {
      pageNumber: 1,
      numPerPage: rowsPerPage,
      groupIDs: filterGroups?.map((g) => g.id).join(),
    };
    if (filterListQueryString !== null) {
      data = {
        ...data,
        annotationFilterList: filterListQueryString,
      };
    }

    if (selectedAnnotationSortOptions !== null) {
      data = {
        ...data,
        sortByAnnotationOrigin: selectedAnnotationSortOptions.origin,
        sortByAnnotationKey: selectedAnnotationSortOptions.key,
        sortByAnnotationOrder: selectedAnnotationSortOptions.order,
      };
    }

    if (filterFormData !== null) {
      data = {
        ...data,
        ...filterFormData,
      };
    }

    await dispatch(candidatesActions.fetchCandidates(data));

    setQueryInProgress(false);
  };

  const handleFilterAdd = ({ formData }) => {
    if (filterGroups.length === 0) {
      dispatch(
        showNotification("At least one program should be selected.", "warning")
      );
      return;
    }
    // The key is actually a combination of `origin<>key`, so parse out the key part
    const key = formData.key.split("<>")[1];
    const annotationObj = { ...formData, key };
    const filterListChip = filterAnnotationObjToChip(annotationObj);
    const filterListQueryItem = JSON.stringify(annotationObj);

    setTableFilterList(tableFilterList.concat([filterListChip]));
    const newFilterListQueryStrings = filterListQueryStrings.concat([
      filterListQueryItem,
    ]);
    setFilterListQueryStrings(newFilterListQueryStrings);

    handleFilterSubmit(newFilterListQueryStrings.join());
  };

  const [ps1GenerationInProgressList, setPS1GenerationInProgressList] =
    useState([]);
  const generatePS1Thumbnail = (objID) => {
    setPS1GenerationInProgressList([...ps1GenerationInProgressList, objID]);
    dispatch(candidatesActions.generatePS1Thumbnail(objID));
  };

  const handleViewColumnsChange = (changedColumn, action) => {
    let selectedColumns = [];
    if (action === "remove") {
      selectedColumns = viewColumns?.filter((col) => col !== changedColumn);
    } else {
      selectedColumns = [...viewColumns, changedColumn];
    }
    setViewColumns(selectedColumns);
  };

  const renderThumbnails = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    const hasPS1 = candidateObj?.thumbnails
      ?.map((t) => t.type)
      ?.includes("ps1");
    const displayTypes = hasPS1
      ? ["new", "ref", "sub", "sdss", "dr8", "ps1"]
      : ["new", "ref", "sub", "sdss", "dr8"];
    return (
      <div className={classes.thumbnails}>
        <ThumbnailList
          ra={candidateObj.ra}
          dec={candidateObj.dec}
          thumbnails={candidateObj.thumbnails}
          size="9rem"
          displayTypes={displayTypes}
        />
        {!hasPS1 && (
          <Button
            disabled={ps1GenerationInProgressList.includes(candidateObj.id)}
            size="small"
            variant="contained"
            onClick={() => {
              generatePS1Thumbnail(candidateObj.id);
            }}
            data-testid={`generatePS1Button${candidateObj.id}`}
          >
            Generate PS1 Cutout
          </Button>
        )}
      </div>
    );
  };

  const renderInfo = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    const recentClassification =
      candidateObj.classifications && candidateObj.classifications.length > 0
        ? getMostRecentClassification(candidateObj.classifications)
        : null;

    return (
      <div className={classes.info}>
        <span className={classes.itemPaddingBottom}>
          <a
            href={`/source/${candidateObj.id}`}
            target="_blank"
            data-testid={candidateObj.id}
            rel="noreferrer"
          >
            <Button
              variant="contained"
              size="small"
              color="primary"
              className={classes.idButton}
            >
              {candidateObj.id}&nbsp;
              <OpenInNewIcon fontSize="inherit" />
            </Button>
          </a>
        </span>
        {candidateObj.is_source ? (
          <div>
            <div className={classes.itemPaddingBottom}>
              <Chip size="small" label="Previously Saved" color="primary" />
              <RejectButton objID={candidateObj.id} />
            </div>
            <div className={classes.saveCandidateButton}>
              <EditSourceGroups
                source={{
                  id: candidateObj.id,
                  currentGroupIds: candidateObj.saved_groups?.map((g) => g.id),
                }}
                groups={allGroups}
              />
            </div>
            <div>
              <AddClassificationsScanningPage obj_id={candidateObj.id} />
            </div>
            <div className={classes.infoItem}>
              <b>Saved groups: </b>
              <span>
                {candidateObj.saved_groups?.map((group) => (
                  <Chip
                    label={
                      group.nickname
                        ? group.nickname.substring(0, 15)
                        : group.name.substring(0, 15)
                    }
                    key={group.id}
                    size="small"
                    className={classes.chip}
                  />
                ))}
              </span>
            </div>
          </div>
        ) : (
          <div>
            <Chip
              size="small"
              label="NOT SAVED"
              className={classes.itemPaddingBottom}
            />
            <RejectButton objID={candidateObj.id} />
          </div>
        )}
        {/* If candidate is either unsaved or is not yet saved to all groups being filtered on, show the "Save to..." button */}
        {Boolean(
          !candidateObj.is_source ||
            (candidateObj.is_source &&
              filterGroups?.filter(
                (g) =>
                  !candidateObj.saved_groups?.map((x) => x.id)?.includes(g.id)
              ).length)
        ) && (
          // eslint-disable-next-line react/jsx-indent
          <div className={classes.saveCandidateButton}>
            <SaveCandidateButton
              candidate={candidateObj}
              userGroups={
                // Filter out groups the candidate is already saved to
                candidateObj.is_source
                  ? userAccessibleGroups?.filter(
                      (g) =>
                        !candidateObj.saved_groups
                          ?.map((x) => x.id)
                          ?.includes(g.id)
                    )
                  : userAccessibleGroups
              }
              filterGroups={
                // Filter out groups the candidate is already saved to
                candidateObj.is_source
                  ? filterGroups?.filter(
                      (g) =>
                        !candidateObj.saved_groups
                          ?.map((x) => x.id)
                          ?.includes(g.id)
                    )
                  : filterGroups
              }
            />
          </div>
        )}
        {candidateObj.last_detected_at && (
          <div className={classes.infoItem}>
            <b>Last detected: </b>
            <span>
              {
                String(candidateObj.last_detected_at)
                  .split(".")[0]
                  .split("T")[1]
              }
              &nbsp;&nbsp;
              {
                String(candidateObj.last_detected_at)
                  .split(".")[0]
                  .split("T")[0]
              }
            </span>
          </div>
        )}
        <div className={classes.infoItem}>
          <b>Coordinates: </b>
          <span className={classes.position}>
            {ra_to_hours(candidateObj.ra)} &nbsp;
            {dec_to_dms(candidateObj.dec)}
          </span>
          &nbsp; (&alpha;,&delta;= {candidateObj.ra.toFixed(3)}, &nbsp;
          {candidateObj.dec.toFixed(3)})
        </div>
        <div className={classes.infoItem}>
          <b>Gal. Coords (l,b): </b>
          <span>
            {candidateObj.gal_lon.toFixed(3)}&nbsp;&nbsp;
            {candidateObj.gal_lat.toFixed(3)}
          </span>
        </div>
        {candidateObj.classifications && recentClassification && (
          <div className={classes.infoItemPadded}>
            <b>Classification: </b>
            <br />
            <span>
              <Chip
                size="small"
                label={recentClassification}
                color="primary"
                className={classes.chip}
              />
            </span>
          </div>
        )}
        {selectedAnnotationSortOptions !== null &&
          candidateHasAnnotationWithSelectedKey(candidateObj) && (
            <div className={classes.infoItem}>
              <b>
                {selectedAnnotationSortOptions.key} (
                {selectedAnnotationSortOptions.origin}):
              </b>
              <span>{getCandidateSelectedAnnotationValue(candidateObj)}</span>
            </div>
          )}
      </div>
    );
  };

  const renderPhotometry = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <Suspense fallback={<Spinner />}>
        <VegaPhotometry sourceId={candidateObj.id} />
      </Suspense>
    );
  };

  const renderAutoannotations = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <div className={classes.annotations}>
        {candidateObj.annotations && (
          <ScanningPageCandidateAnnotations
            annotations={candidateObj.annotations}
          />
        )}
      </div>
    );
  };

  const renderAutoannotationsHeader = () => (
    <div>
      Autoannotations
      <IconButton
        aria-label="help"
        size="small"
        onClick={handleClickAnnotationsHelp}
        className={classes.helpButton}
      >
        <HelpOutlineIcon />
      </IconButton>
      <MuiThemeProvider theme={getMuiPopoverTheme(theme)}>
        <Popover
          id={annotationsHelpId}
          open={annotationsHelpOpen}
          anchorEl={annotationsHeaderAnchor}
          onClose={handleCloseAnnotationsHelp}
          className={classes.helpPopover}
          anchorOrigin={{
            vertical: "top",
            horizontal: "right",
          }}
          transformOrigin={{
            vertical: "top",
            horizontal: "left",
          }}
        >
          <Typography className={classes.typography}>
            Annotation fields are uniquely identified by the combination of
            origin and key. That is, two annotation values belonging to a key
            with the same name will be considered different if they come from
            different origins. <br />
            <b>Sorting: </b> Clicking on an annotation field will display it, if
            available, in the Info column. You can then click on the sort tool
            button at the top of the table to sort on that annotation field. You
            can also set the initial sorting parameters when submitting a new
            candidates search via the form at the top of the page.
            <br />
            <b>Filtering: </b> Filtering on annotations is available through the
            filtering tool at the top right of the table. <br />
            <i>
              Warning: applying multiple filters on annotations from different
              origins is not supported currently and will return zero results.
              For example, you cannot filter for a specific annotation value in
              annotations from both &quot;origin_a&quot; and
              &quot;origin_b&quot; at the same time.
            </i>
          </Typography>
        </Popover>
      </MuiThemeProvider>
    </div>
  );

  const handlePageChange = async (page, numPerPage) => {
    setQueryInProgress(true);
    // API takes 1-indexed page number
    let data = {
      pageNumber: page + 1,
      numPerPage,
      queryID,
      groupIDs: filterGroups?.map((g) => g.id)?.join(),
    };
    if (selectedAnnotationSortOptions !== null) {
      data = {
        ...data,
        sortByAnnotationOrigin: selectedAnnotationSortOptions.origin,
        sortByAnnotationKey: selectedAnnotationSortOptions.key,
        sortByAnnotationOrder: selectedAnnotationSortOptions.order,
      };
    }

    if (filterListQueryStrings.length !== 0) {
      data = {
        ...data,
        annotationFilterList: filterListQueryStrings.join(),
      };
    }

    if (filterFormData !== null) {
      data = {
        ...data,
        ...filterFormData,
      };
    }

    await dispatch(candidatesActions.fetchCandidates(data));
    setQueryInProgress(false);
  };

  const handleTableChange = (action, tableState) => {
    setRowsPerPage(tableState.rowsPerPage);
    switch (action) {
      case "changePage":
      case "changeRowsPerPage":
        handlePageChange(tableState.page, tableState.rowsPerPage);
        break;
      default:
    }
  };

  const handleTableFilterChipChange = (column, filterList, type) => {
    if (type === "chip") {
      const annotationsFilterList = filterList[3];
      setTableFilterList(annotationsFilterList);
      const newFilterListQueryStrings = annotationsFilterList?.map((chip) => {
        const annotationObject = filterChipToAnnotationObj(chip);
        return JSON.stringify(annotationObject);
      });
      setFilterListQueryStrings(newFilterListQueryStrings);

      handleFilterSubmit(
        newFilterListQueryStrings.length === 0
          ? null
          : newFilterListQueryStrings.join()
      );
    }
  };

  // Assemble json form schema for possible annotation filtering values
  const filterFormSchema = {
    description: "Add an annotation filter field.",
    type: "object",
    properties: {
      origin: {
        type: "string",
        title: "Origin",
        enum: [],
      },
    },
    required: ["origin", "key"],
    dependencies: {
      origin: {
        oneOf: [],
      },
      key: {
        oneOf: [],
      },
    },
  };

  if (availableAnnotationsInfo !== null) {
    Object.entries(availableAnnotationsInfo).forEach(([origin, fields]) => {
      // Add origin to the list selectable from
      filterFormSchema.properties.origin.enum.push(origin);

      // Make a list of keys to select from based on the origin
      // We tack on the origin (using a separator that shouldn't be part of expected
      // origin or key strings ('<>')) so that keys that are common across origin
      // get their own fields in the form schema.
      const keySelect = {
        properties: {
          origin: {
            enum: [origin],
          },
          key: {
            type: "string",
            title: "Key",
            enum: fields?.map((field) => `${origin}<>${Object.keys(field)[0]}`),
            enumNames: fields?.map((field) => Object.keys(field)[0]),
          },
        },
      };
      filterFormSchema.dependencies.origin.oneOf.push(keySelect);

      // Add filter value selection based on selected key type
      fields.forEach((field) => {
        const key = Object.keys(field)[0];
        const keyType = field[key];
        const valueSelect = {
          properties: {
            key: {
              enum: [`${origin}<>${key}`],
            },
          },
          required: [],
        };
        switch (keyType) {
          case "string":
          case "object":
            valueSelect.properties.value = {
              type: "string",
              title: "Value (exact match)",
            };
            valueSelect.required.push("value");
            break;
          case "number":
            valueSelect.properties.min = {
              type: "number",
              title: "Min",
            };
            valueSelect.properties.max = {
              type: "number",
              title: "Max",
            };
            valueSelect.required.push("min");
            valueSelect.required.push("max");
            break;
          case "boolean":
            valueSelect.properties.value = {
              type: "boolean",
              title: "Is True",
              default: false,
            };
            valueSelect.required.push("value");
            break;
          default:
            break;
        }
        filterFormSchema.dependencies.key.oneOf.push(valueSelect);
      });
    });
  }

  const annotationsFilterDisplay = () =>
    !queryInProgress ? (
      <div>
        <Form schema={filterFormSchema} onSubmit={handleFilterAdd} />
      </div>
    ) : (
      <div />
    );

  const columns = [
    {
      name: "Images",
      label: "Images",
      options: {
        display: viewColumns.includes("Images"),
        customBodyRenderLite: renderThumbnails,
        sort: false,
        filter: false,
      },
    },
    {
      name: "Info",
      label: "Info",
      options: {
        display: viewColumns.includes("Info"),
        customBodyRenderLite: renderInfo,
        filter: false,
      },
    },
    {
      name: "Photometry",
      label: "Photometry",
      options: {
        display: viewColumns.includes("Photometry"),
        customBodyRenderLite: renderPhotometry,
        sort: false,
        filter: false,
      },
    },
    {
      name: "Autoannotations",
      label: "Autoannotations",
      options: {
        display: viewColumns.includes("Autoannotations"),
        customBodyRenderLite: renderAutoannotations,
        sort: false,
        filter: !queryInProgress,
        filterType: "custom",
        filterList: tableFilterList,
        filterOptions: {
          // eslint-disable-next-line react/display-name
          display: annotationsFilterDisplay,
        },
        customHeadLabelRender: renderAutoannotationsHeader,
      },
    },
  ];

  const options = {
    responsive: "vertical",
    search: false,
    print: false,
    download: false,
    sort: false,
    filter: !queryInProgress,
    filterType: "custom",
    count: totalMatches,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    rowsPerPage,
    rowsPerPageOptions: [1, 25, 50, 75, 100, 200],
    jumpToPage: true,
    serverSide: true,
    page: pageNumber - 1,
    pagination: true,
    rowHover: false,
    onTableChange: handleTableChange,
    // eslint-disable-next-line react/display-name
    customToolbar: () => (
      <CustomSortToolbar
        selectedAnnotationSortOptions={selectedAnnotationSortOptions}
        rowsPerPage={rowsPerPage}
        filterGroups={filterGroups}
        filterFormData={filterFormData}
        setQueryInProgress={setQueryInProgress}
        loaded={!queryInProgress}
        sortOrder={sortOrder}
        setSortOrder={setSortOrder}
      />
    ),
    onFilterChange: handleTableFilterChipChange,
    onViewColumnsChange: handleViewColumnsChange,
  };

  return (
    <Paper elevation={1}>
      <div className={classes.candidateListContainer}>
        <Typography variant="h6" className={classes.title}>
          Scan candidates for sources
        </Typography>
        <FilterCandidateList
          userAccessibleGroups={userAccessibleGroups}
          setQueryInProgress={setQueryInProgress}
          setFilterGroups={setFilterGroups}
          numPerPage={rowsPerPage}
          annotationFilterList={filterListQueryStrings.join()}
          setSortOrder={setSortOrder}
        />
        <Box
          display={queryInProgress ? "block" : "none"}
          className={classes.spinnerDiv}
        >
          <Spinner />
        </Box>
        <Box display={queryInProgress ? "none" : "block"}>
          <MuiThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              // Reset key to reset page number
              // https://github.com/gregnb/mui-datatables/issues/1166
              key={`table_${pageNumber}`}
              columns={columns}
              data={candidates !== null ? candidates : []}
              className={classes.table}
              options={options}
            />
          </MuiThemeProvider>
        </Box>
      </div>
      <div className={classes.pages}>
        <div>
          <Button
            variant="contained"
            onClick={() => {
              window.scrollTo({ top: 0 });
            }}
            size="small"
          >
            Back to top <ArrowUpward />
          </Button>
        </div>
      </div>
    </Paper>
  );
};

export default CandidateList;
