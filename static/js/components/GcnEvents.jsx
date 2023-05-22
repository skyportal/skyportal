import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
} from "@mui/material/styles";
import { withStyles, makeStyles } from "@mui/styles";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import JoinInnerIcon from "@mui/icons-material/JoinInner";
import InfoIcon from "@mui/icons-material/Info";
import Close from "@mui/icons-material/Close";
import grey from "@mui/material/colors/grey";

import MUIDataTable from "mui-datatables";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import Button from "./Button";

import { filterOutEmptyValues } from "../API";
import * as gcnEventsActions from "../ducks/gcnEvents";
import Spinner from "./Spinner";
import GcnEventsFilterForm from "./GcnEventsFilterForm";
import NewGcnEvent from "./NewGcnEvent";
import Crossmatch from "./CrossmatchGcnEvents";
import GcnEventAllocationTriggers from "./GcnEventAllocationTriggers";

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  eventTags: {
    marginLeft: "0.5rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
  gcnEventLink: {
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
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    overrides: {
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
  )
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
  const [openCrossmatch, setOpenCrossmatch] = useState(false);

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
    const data = filterOutEmptyValues(formData);
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
        tableState.sortOrder
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
      <Chip size="small" key={tag} label={tag} className={classes.eventTags} />
    ));
  };

  const renderGcnNotices = (dataIndex) => (
    <ul>
      {events[dataIndex]?.gcn_notices?.map((gcnNotice) => (
        <li key={gcnNotice.id}>
          {["date", "ivorn", "dateobs", "stream"].map((attr) => (
            <p key={attr}>
              {attr}: {gcnNotice[attr]}
            </p>
          ))}
        </li>
      ))}
    </ul>
  );

  const renderLocalizations = (dataIndex) => (
    <ul>
      {events[dataIndex]?.localizations?.map((loc) => (
        <li key={loc.id}>
          {["localization_name", "dateobs"].map((attr) => (
            <p key={attr}>
              {attr}: {loc[attr]}
            </p>
          ))}
        </li>
      ))}
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
      },
    },
    {
      name: "gcn_tags",
      label: "Event Tags",
      options: {
        customBodyRenderLite: renderGcnTags,
        filter: false,
      },
    },
    {
      name: "allocation_triggers",
      label: "Allocation Triggers",
      options: {
        customBodyRenderLite: renderAllocationTriggers,
        filter: false,
      },
    },
    {
      name: "localization_tags",
      label: "Localization Tags",
      options: {
        customBodyRenderLite: renderLocalizationTags,
        filter: false,
      },
    },
    {
      name: "localizations",
      label: "Localizations",
      options: {
        customBodyRenderLite: renderLocalizations,
        filter: false,
      },
    },
    {
      name: "gcn_notices",
      label: "GCN Notices",
      options: {
        customBodyRenderLite: renderGcnNotices,
        filter: false,
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
      </Grid>
    </Grid>
  );
};

export default GcnEvents;
