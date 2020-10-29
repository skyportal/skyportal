import React, { useEffect, Suspense, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useHistory } from "react-router-dom";
import PropTypes from "prop-types";

import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import {
  makeStyles,
  createMuiTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";
import useMediaQuery from "@material-ui/core/useMediaQuery";
import Button from "@material-ui/core/Button";
import IconButton from "@material-ui/core/IconButton";
import CircularProgress from "@material-ui/core/CircularProgress";
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

import * as candidatesActions from "../ducks/candidates";
import ThumbnailList from "./ThumbnailList";
import SaveCandidateButton from "./SaveCandidateButton";
import FilterCandidateList from "./FilterCandidateList";
import ScanningPageCandidateAnnotations, {
  getAnnotationValueString,
} from "./ScanningPageCandidateAnnotations";
import EditSourceGroups from "./EditSourceGroups";
import { ra_to_hours, dec_to_dms } from "../units";

const VegaPlot = React.lazy(() =>
  import(/* webpackChunkName: "VegaPlot" */ "./VegaPlot")
);

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
}));

// Tweak responsive column widths
const getMuiTheme = (theme) =>
  createMuiTheme({
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
    },
  });

const getMostRecentClassification = (classifications) => {
  // Display the most recent non-zero probability class
  const filteredClasses = classifications.filter((i) => i.probability > 0);
  const sortedClasses = filteredClasses.sort((a, b) =>
    a.modified < b.modified ? 1 : -1
  );

  return `${sortedClasses[0].classification}`;
};

const getMuiPopoverTheme = () =>
  createMuiTheme({
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
  filterFormData,
  setQueryInProgress,
  loaded,
}) => {
  const classes = useStyles();

  const [sortOrder, setSortOrder] = useState(
    selectedAnnotationSortOptions ? selectedAnnotationSortOptions.order : null
  );
  const dispatch = useDispatch();

  const handleSort = async () => {
    const newSortOrder =
      sortOrder === null || sortOrder === "desc" ? "asc" : "desc";
    setSortOrder(newSortOrder);

    setQueryInProgress(true);
    let data = {
      pageNumber: 1,
      numPerPage: rowsPerPage,
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
  filterFormData: PropTypes.shape({}).isRequired,
  loaded: PropTypes.bool.isRequired,
};

CustomSortToolbar.defaultProps = {
  selectedAnnotationSortOptions: null,
};

const CandidateList = () => {
  const history = useHistory();
  const [queryInProgress, setQueryInProgress] = useState(false);
  const [rowsPerPage, setRowsPerPage] = useState(defaultNumPerPage);
  const [filterGroups, setFilterGroups] = useState([]);
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
    lastPage,
    totalMatches,
    numberingStart,
    numberingEnd,
    selectedAnnotationSortOptions,
  } = useSelector((state) => state.candidates);

  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible
  );

  useEffect(() => {
    if (userAccessibleGroups?.length && filterGroups.length === 0) {
      setFilterGroups([...userAccessibleGroups]);
    }
  }, [setFilterGroups, filterGroups, userAccessibleGroups]);

  const availableAnnotationsInfo = useSelector(
    (state) => state.candidates.annotationsInfo
  );

  const filterFormData = useSelector(
    (state) => state.candidates.filterFormData
  );

  const dispatch = useDispatch();

  useEffect(() => {
    if (candidates === null) {
      setQueryInProgress(true);
      dispatch(
        candidatesActions.fetchCandidates({ numPerPage: defaultNumPerPage })
      );
      // Grab the available annotation fields for filtering
      dispatch(candidatesActions.fetchAnnotationsInfo());
    } else {
      setQueryInProgress(false);
    }
  }, [candidates, dispatch]);

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

  const filterAnnotationObjToChip = (annotationObj) => {
    // Convert an object representing an annotation filter to a formatted string
    // to be displayed by the MuiDataTable
    return "value" in annotationObj
      ? `${annotationObj.key} (${annotationObj.origin}): ${annotationObj.value}`
      : `${annotationObj.key} (${annotationObj.origin}): ${annotationObj.min} - ${annotationObj.max}`;
  };

  const handleFilterSubmit = async (filterListQueryString) => {
    setQueryInProgress(true);

    let data = {
      pageNumber: 1,
      numPerPage: rowsPerPage,
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
    const filterListChip = filterAnnotationObjToChip(formData);
    const filterListQueryItem = JSON.stringify(formData);

    setTableFilterList(tableFilterList.concat([filterListChip]));
    const newFilterListQueryStrings = filterListQueryStrings.concat([
      filterListQueryItem,
    ]);
    setFilterListQueryStrings(newFilterListQueryStrings);

    handleFilterSubmit(newFilterListQueryStrings.join());
  };

  const renderThumbnails = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <div className={classes.thumbnails}>
        <ThumbnailList
          ra={candidateObj.ra}
          dec={candidateObj.dec}
          thumbnails={candidateObj.thumbnails}
          size="9rem"
          displayTypes={["new", "ref", "sub", "sdss", "dr8"]}
        />
      </div>
    );
  };

  const renderInfo = (dataIndex) => {
    const candidateObj = candidates[dataIndex];
    return (
      <div className={classes.info}>
        <span className={classes.itemPaddingBottom}>
          <b>ID:</b>&nbsp;
          <a
            href={`/candidate/${candidateObj.id}`}
            target="_blank"
            rel="noreferrer"
          >
            {candidateObj.id}&nbsp;
            <OpenInNewIcon fontSize="inherit" />
          </a>
        </span>
        <br />
        {candidateObj.is_source ? (
          <div>
            <div className={classes.itemPaddingBottom}>
              <Chip
                size="small"
                label="Previously Saved"
                clickable
                onClick={() => history.push(`/source/${candidateObj.id}`)}
                onDelete={() =>
                  window.open(`/source/${candidateObj.id}`, "_blank")
                }
                deleteIcon={<OpenInNewIcon />}
                color="primary"
              />
            </div>
            <div className={classes.saveCandidateButton}>
              <EditSourceGroups
                source={{
                  id: candidateObj.id,
                  currentGroupIds: candidateObj.saved_groups.map((g) => g.id),
                }}
                userGroups={userAccessibleGroups}
              />
            </div>
            <div className={classes.infoItem}>
              <b>Saved groups: </b>
              <span>
                {candidateObj.saved_groups.map((group) => (
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
            <br />
            <div className={classes.saveCandidateButton}>
              <SaveCandidateButton
                candidate={candidateObj}
                userGroups={userAccessibleGroups}
                filterGroups={filterGroups}
              />
            </div>
          </div>
        )}
        {candidateObj.last_detected && (
          <div className={classes.infoItem}>
            <b>Last detected: </b>
            <span>
              {String(candidateObj.last_detected).split(".")[0].split("T")[1]}
              &nbsp;&nbsp;
              {String(candidateObj.last_detected).split(".")[0].split("T")[0]}
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
        {candidateObj.classifications &&
          candidateObj.classifications.length > 0 && (
            <div className={classes.infoItem}>
              <b>Classification: </b>
              <span>
                {getMostRecentClassification(candidateObj.classifications)}
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
      <Suspense fallback={<CircularProgress />}>
        <VegaPlot dataUrl={`/api/sources/${candidateObj.id}/photometry`} />
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

  const renderAutoannotationsHeader = () => {
    return (
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
              origin and key. That is, if two annotation values belong to a key
              with the same name will be considered different if they come from
              different origins. <br />
              <b>Sorting: </b> Clicking on an annotation field will display it,
              if available, in the Info column. You can then click on the sort
              tool button at the top of the table to sort on that annotation
              field.
            </Typography>
          </Popover>
        </MuiThemeProvider>
      </div>
    );
  };

  const handlePageChange = async (page, numPerPage) => {
    setQueryInProgress(true);
    // API takes 1-indexed page number
    let data = { pageNumber: page + 1, numPerPage };
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
      const newFilterListQueryStrings = annotationsFilterList.map((chip) => {
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
      const keySelect = {
        properties: {
          origin: {
            enum: [origin],
          },
          key: {
            type: "string",
            title: "Key",
            enum: fields.map((field) => Object.keys(field)[0]),
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
              enum: [key],
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

  const annotationsFilterDisplay = () => {
    return !queryInProgress ? (
      <div>
        <Form schema={filterFormSchema} onSubmit={handleFilterAdd} />
      </div>
    ) : (
      <div />
    );
  };

  const columns = [
    {
      name: "Images",
      label: "Images",
      options: {
        customBodyRenderLite: renderThumbnails,
        sort: false,
        filter: false,
      },
    },
    {
      name: "Info",
      label: "Info",
      options: {
        customBodyRenderLite: renderInfo,
        filter: false,
      },
    },
    {
      name: "Photometry",
      label: "Photometry",
      options: {
        customBodyRenderLite: renderPhotometry,
        sort: false,
        filter: false,
      },
    },
    {
      name: "Autoannotations",
      label: "Autoannotations",
      options: {
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
        filterFormData={filterFormData}
        setQueryInProgress={setQueryInProgress}
        loaded={!queryInProgress}
      />
    ),
    onFilterChange: handleTableFilterChipChange,
  };

  return (
    <Paper elevation={1}>
      <div className={classes.candidateListContainer}>
        <Typography variant="h6" className={classes.title}>
          Scan candidates for sources
        </Typography>
        <FilterCandidateList
          userAccessibleGroups={userAccessibleGroups}
          pageNumber={pageNumber}
          numberingStart={numberingStart}
          numberingEnd={numberingEnd}
          lastPage={lastPage}
          totalMatches={totalMatches}
          setQueryInProgress={setQueryInProgress}
          setFilterGroups={setFilterGroups}
        />
        <Box
          display={queryInProgress ? "block" : "none"}
          className={classes.spinnerDiv}
        >
          <CircularProgress />
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
