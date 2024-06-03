import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import { makeStyles, withStyles } from "@mui/styles";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import JoinInnerIcon from "@mui/icons-material/JoinInner";
import InfoIcon from "@mui/icons-material/Info";
import LocalOfferIcon from "@mui/icons-material/LocalOffer";
import Close from "@mui/icons-material/Close";
import grey from "@mui/material/colors/grey";

import MUIDataTable from "mui-datatables";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import Tooltip from "@mui/material/Tooltip";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import ExpandLess from "@mui/icons-material/ExpandLess";
import Button from "../Button";

import { filterOutEmptyValues } from "../../API";
import * as gcnEventsActions from "../../ducks/gcnEvents";
import Spinner from "../Spinner";
import GcnEventsFilterForm from "./GcnEventsFilterForm";
import NewGcnEvent from "../NewGcnEvent";
import DefaultGcnTagPage from "../DefaultGcnTagPage";
import Crossmatch from "../CrossmatchGcnEvents";
import GcnEventAllocationTriggers from "./GcnEventAllocationTriggers";

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  tags: {
    margin: "0 1px 1px 0",
    "& > div": {
      margin: "0.25rem",
    },
  },
  gcnEventLink: {
    padding: 0,
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
  },
  filterAlert: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-start",
    marginTop: "1rem",
  },
  list: {
    listStyleType: "none",
    paddingLeft: 0,
    margin: 0,
    "& li:not(:first-child)": {
      position: "relative",
      marginTop: theme.spacing(2),
      "&:before": {
        content: `""`,
        backgroundColor: theme.palette.grey[400],
        position: "absolute",
        top: theme.spacing(-1),
        left: "0",
        width: "20%",
        height: "1px",
      },
    },
    "& div": {
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      "& a": {
        cursor: "pointer",
      },
    },
  },
  smallText: {
    fontSize: "0.7rem",
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTable: {
        styleOverrides: {
          root: {
            "& p": {
              margin: 0,
            },
          },
        },
      },
      MUIDataTableToolbar: {
        styleOverrides: {
          root: {
            maxHeight: "2rem",
            padding: "0 0.75rem",
            margin: 0,
          },
        },
      },
      MUIDataTableHeadCell: {
        styleOverrides: {
          root: {
            padding: `${theme.spacing(1)} ${theme.spacing(2.5)} ${theme.spacing(
              1,
            )} ${theme.spacing(1.5)}`,
          },
        },
      },
      MUIDataTableBodyCell: {
        styleOverrides: {
          stackedParent: {
            padding: `${theme.spacing(1)} ${theme.spacing(2.5)} ${theme.spacing(
              1,
            )} ${theme.spacing(1.5)}`,
            verticalAlign: "top",
          },
        },
      },
      MuiIconButton: {
        root: {
          padding: "0.5rem",
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
        tableCellContainer: {
          padding: "1rem",
        },
        selectRoot: {
          marginRight: "0.5rem",
          [theme.breakpoints.up("sm")]: {
            marginLeft: "0",
            marginRight: "2rem",
          },
        },
      },
    },
  });

const dialogTitleStyles = (theme) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  title: {
    marginRight: theme.spacing(2),
    fontSize: "1.5rem",
  },
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(dialogTitleStyles)(
  ({ children, classes, onClose }) => (
    <MuiDialogTitle className={classes.root}>
      <Typography className={classes.title}>{children}</Typography>
      {onClose ? (
        <IconButton
          aria-label="close"
          className={classes.closeButton}
          onClick={onClose}
        >
          <Close />
        </IconButton>
      ) : null}
    </MuiDialogTitle>
  ),
);

const defaultNumPerPage = 10;

const GcnEvents = () => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();
  const gcnEvents = useSelector((state) => state.gcnEvents);
  const [filterFormSubmitted, setFilterFormSubmitted] = useState(false);

  const gcn_tags_classes = useSelector((state) => state.config.gcnTagsClasses);

  const [openNew, setOpenNew] = useState(false);
  const [showAllLocalizations, setShowAllLocalizations] = useState(false);
  const [showAllNotices, setShowAllNotices] = useState(false);
  const [openCrossmatch, setOpenCrossmatch] = useState(false);
  const [openDefaultTag, setOpenDefaultTag] = useState(false);

  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  useEffect(() => {
    dispatch(gcnEventsActions.fetchGcnEvents());
  }, [dispatch]);

  if (!gcnEvents) {
    return <p>No gcnEvents available...</p>;
  }

  const { events, totalMatches } = gcnEvents;

  const handleClose = () => {
    setOpenNew(false);
    setOpenCrossmatch(false);
    setOpenDefaultTag(false);
  };

  const handlePageChange = async (pageNumber, numPerPage, sortData) => {
    const params = {
      ...fetchParams,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      params.sortBy = sortData.name;
      params.sortOrder = sortData.direction;
    }
    // Save state for future
    setFetchParams(params);
    await dispatch(gcnEventsActions.fetchGcnEvents(params));
  };

  const handleTableFilter = async (pageNumber, numPerPage, filterData) => {
    const params = {
      ...fetchParams,
      pageNumber,
      numPerPage,
    };
    if (filterData && Object.keys(filterData).length > 0) {
      params.startDate = filterData.startDate;
      params.endDate = filterData.endDate;
      params.gcnTagKeep = filterData.gcnTagKeep;
      params.gcnTagRemove = filterData.gcnTagRemove;
      params.gcnPropertiesFilter = filterData.gcnPropertiesFilter;
      params.localizationTagKeep = filterData.localizationTagKeep;
      params.localizationTagRemove = filterData.localizationTagRemove;
      params.localizationPropertiesFilter =
        filterData.localizationPropertiesFilter;
    }
    // Save state for future
    setFetchParams(params);
    await dispatch(gcnEventsActions.fetchGcnEvents(params));
  };

  const handleTableSorting = async (sortData) => {
    const params = {
      ...fetchParams,
      pageNumber: 1,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchParams(params);
    await dispatch(gcnEventsActions.fetchGcnEvents(params));
  };

  const handleFilterSubmit = async (formData) => {
    const data = filterOutEmptyValues(formData, false);
    if ("property" in data) {
      data.propertiesFilter = `${data.property}: ${data.propertyComparatorValue}: ${data.propertyComparator}`;
    }
    handleTableFilter(1, defaultNumPerPage, data);
    setFilterFormSubmitted(true);
  };

  const handleSearchChange = async (searchText) => {
    const params = {
      ...fetchParams,
      pageNumber: 1,
      partialdateobs: searchText,
    };
    setFetchParams(params);
    await dispatch(gcnEventsActions.fetchGcnEvents(params));
  };

  // eslint-disable-next-line no-unused-vars
  const handleFilterReset = async (props) => {
    const params = {
      pageNumber: 1,
    };
    setFetchParams(params);
    await dispatch(gcnEventsActions.fetchGcnEvents(params));
    setFilterFormSubmitted(false);
  };

  const handleTableChange = (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      handlePageChange(
        tableState.page + 1,
        tableState.rowsPerPage,
        tableState.sortOrder,
      );
    }
    if (action === "sort") {
      if (tableState.sortOrder.direction === "none") {
        handlePageChange(1, tableState.rowsPerPage, {});
      } else {
        handleTableSorting(tableState.sortOrder);
      }
    }
  };

  const renderGcnTags = (dataIndex) => {
    const gcnTags = [];
    events[dataIndex]?.tags?.forEach((tag) => {
      gcnTags.push(tag);
    });
    const gcnTagsUnique = [...new Set(gcnTags)];
    return gcnTagsUnique.map((tag) => (
      <Chip
        size="small"
        key={tag}
        label={tag}
        className={classes.tags}
        style={{
          backgroundColor:
            gcn_tags_classes && tag in gcn_tags_classes
              ? gcn_tags_classes[tag]
              : "#999999",
        }}
      />
    ));
  };

  const renderAllocationTriggers = (dataIndex) => (
    <GcnEventAllocationTriggers gcnEvent={events[dataIndex]} showPassed />
  );

  const renderLocalizationTags = (dataIndex) => {
    const localizationTags = [];
    events[dataIndex].localizations?.forEach((loc) => {
      loc.tags?.forEach((tag) => {
        localizationTags.push(tag.text);
      });
    });
    const localizationTagsUnique = [...new Set(localizationTags)];
    return localizationTagsUnique.map((tag) => (
      <Chip size="small" key={tag} label={tag} className={classes.tags} />
    ));
  };

  const expandButton = (setShowAll, showAll, cellToProcess) => (
    <div className={classes.expandButton}>
      <IconButton
        aria-label="expandButton"
        onClick={() =>
          setShowAll(showAll === cellToProcess ? false : cellToProcess)
        }
        size="small"
      >
        {showAll === cellToProcess ? <ExpandLess /> : <MoreHorizIcon />}
      </IconButton>
    </div>
  );

  const renderLocalizations = (dataIndex) => (
    <ul className={classes.list}>
      {events[dataIndex]?.localizations?.map((loc, index) => (
        <li
          key={loc.id}
          style={
            showAllLocalizations !== dataIndex && index > 2
              ? { display: "none" }
              : {}
          }
        >
          <p>{loc.localization_name}</p>
        </li>
      ))}
      {events[dataIndex]?.localizations?.length > 3 &&
        expandButton(setShowAllLocalizations, showAllLocalizations, dataIndex)}
    </ul>
  );

  const renderGcnNotices = (dataIndex) => (
    <ul className={classes.list}>
      {events[dataIndex]?.gcn_notices?.map((gcnNotice, index) => (
        <li
          key={gcnNotice.id}
          style={
            showAllNotices !== dataIndex && index > 1 ? { display: "none" } : {}
          }
        >
          <Tooltip title={gcnNotice.ivorn} placement="left">
            <p>{gcnNotice.stream}</p>
          </Tooltip>
          <p className={classes.smallText}>{gcnNotice.notice_type}</p>
          <p className={classes.smallText}>{gcnNotice.date}</p>
        </li>
      ))}
      {events[dataIndex]?.gcn_notices?.length > 2 &&
        expandButton(setShowAllNotices, showAllNotices, dataIndex)}
    </ul>
  );

  const renderDateObs = (dataIndex) => (
    <Link to={`/gcn_events/${events[dataIndex]?.dateobs}`}>
      <Button className={classes.gcnEventLink}>
        {events[dataIndex]?.dateobs}
      </Button>
    </Link>
  );

  const renderAliases = (dataIndex) =>
    events[dataIndex]?.aliases?.length > 0 ? (
      <p>{events[dataIndex]?.aliases.join(", ")}</p>
    ) : (
      <p>No aliases</p>
    );

  const customFilterDisplay = () => (
    <div>
      {filterFormSubmitted && (
        <div className={classes.filterAlert}>
          <InfoIcon /> &nbsp; Filters submitted to server!
        </div>
      )}
      <GcnEventsFilterForm handleFilterSubmit={handleFilterSubmit} />
    </div>
  );
  const columns = [
    {
      name: "dateobs",
      label: "Date Observed",
      options: {
        customBodyRenderLite: renderDateObs,
        filter: false,
      },
    },
    {
      name: "aliases",
      label: "Aliases",
      options: {
        customBodyRenderLite: renderAliases,
        filter: false,
        sort: false,
      },
    },
    {
      name: "gcn_tags",
      label: "Event Tags",
      options: {
        customBodyRenderLite: renderGcnTags,
        filter: false,
        sort: false,
      },
    },
    {
      name: "allocation_triggers",
      label: "Allocation Triggers",
      options: {
        customBodyRenderLite: renderAllocationTriggers,
        filter: false,
        sort: false,
      },
    },
    {
      name: "localization_tags",
      label: "Localization Tags",
      options: {
        customBodyRenderLite: renderLocalizationTags,
        filter: false,
        sort: false,
      },
    },
    {
      name: "localizations",
      label: "Localizations",
      options: {
        customBodyRenderLite: renderLocalizations,
        filter: false,
        sort: false,
      },
    },
    {
      name: "gcn_notices",
      label: "GCN Notices",
      options: {
        customBodyRenderLite: renderGcnNotices,
        filter: false,
        sort: false,
      },
    },
  ];

  const options = {
    selectableRows: "none",
    elevation: 0,
    page: fetchParams.pageNumber - 1,
    rowsPerPage: fetchParams.numPerPage,
    rowsPerPageOptions: [10, 25, 50, 100],
    jumpToPage: true,
    serverSide: true,
    pagination: true,
    count: totalMatches,
    onTableChange: handleTableChange,
    search: true, // Disable search for now (not implemented yet)
    onSearchChange: handleSearchChange,
    onFilterChange: handleFilterReset,
    download: false, // Disable download button for now (not implemented yet)
    filter: true,
    customFilterDialogFooter: customFilterDisplay,
    customToolbar: () => (
      <>
        <IconButton
          name="new_gcnevent"
          onClick={() => {
            setOpenNew(true);
          }}
        >
          <AddIcon />
        </IconButton>
        <IconButton
          name="crossmatch_gcnevents"
          onClick={() => {
            setOpenCrossmatch(true);
          }}
        >
          <JoinInnerIcon />
        </IconButton>
        <IconButton
          name="default_gcn_tags"
          onClick={() => {
            setOpenDefaultTag(true);
          }}
        >
          <LocalOfferIcon />
        </IconButton>
      </>
    ),
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={12} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            {gcnEvents ? (
              <StyledEngineProvider injectFirst>
                <ThemeProvider theme={getMuiTheme(theme)}>
                  <MUIDataTable
                    title="GCN Events"
                    data={gcnEvents.events}
                    options={options}
                    columns={columns}
                  />
                </ThemeProvider>
              </StyledEngineProvider>
            ) : (
              <Spinner />
            )}
          </div>
        </Paper>
        {openNew && (
          <Dialog
            open={openNew}
            onClose={handleClose}
            style={{ position: "fixed" }}
            maxWidth="md"
          >
            <DialogTitle onClose={handleClose}>New GCN Event</DialogTitle>
            <DialogContent dividers>
              <NewGcnEvent handleClose={handleClose} />
            </DialogContent>
          </Dialog>
        )}
        {openCrossmatch && (
          <Dialog
            open={openCrossmatch}
            onClose={handleClose}
            style={{ position: "fixed" }}
            maxWidth="md"
          >
            <DialogTitle onClose={handleClose}>
              Crossmatch GCN Events
            </DialogTitle>
            <DialogContent dividers>
              <Crossmatch />
            </DialogContent>
          </Dialog>
        )}
        {openDefaultTag && (
          <Dialog
            open={openDefaultTag}
            onClose={handleClose}
            style={{ position: "fixed" }}
            maxWidth="md"
          >
            <DialogTitle onClose={handleClose}>Default Gcn Tags</DialogTitle>
            <DialogContent dividers>
              <DefaultGcnTagPage />
            </DialogContent>
          </Dialog>
        )}
      </Grid>
    </Grid>
  );
};

export default GcnEvents;
