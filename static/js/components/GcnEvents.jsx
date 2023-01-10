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
  adaptV4Theme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import InfoIcon from "@mui/icons-material/Info";

import MUIDataTable from "mui-datatables";
import Button from "./Button";

import { filterOutEmptyValues } from "../API";
import * as gcnEventsActions from "../ducks/gcnEvents";
import Spinner from "./Spinner";
import GcnEventsFilterForm from "./GcnEventsFilterForm";
import NewGcnEvent from "./NewGcnEvent";
import Crossmatch from "./CrossmatchGcnEvents";

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
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme(
    adaptV4Theme({
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
    })
  );

const defaultNumPerPage = 10;

const GcnEvents = () => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();
  const gcnEvents = useSelector((state) => state.gcnEvents);
  const [filterFormSubmitted, setFilterFormSubmitted] = useState(false);

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
      params.tagKeep = filterData.tagKeep;
      params.tagRemove = filterData.tagRemove;

      if ("gcnProperty" in filterData) {
        if ("gcnPropertyComparatorValue" in filterData) {
          params.gcnPropertiesFilter = `${filterData.gcnProperty}: ${filterData.gcnPropertyComparatorValue}: ${filterData.gcnPropertyComparator}`;
        } else {
          params.gcnPropertiesFilter = `${filterData.gcnProperty}`;
        }
      }
      if ("localizationProperty" in filterData) {
        if ("localizationPropertyComparatorValue" in filterData) {
          params.localizationPropertiesFilter = `${filterData.localizationProperty}: ${filterData.localizationPropertyComparatorValue}: ${filterData.localizationPropertyComparator}`;
        } else {
          params.localizationPropertiesFilter = `${filterData.localizationProperty}`;
        }
      }
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
      <Chip size="small" key={tag} label={tag} className={classes.eventTags} />
    ));
  };

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

  const customFilterDisplay = () =>
    filterFormSubmitted ? (
      <div className={classes.filterAlert}>
        <InfoIcon /> &nbsp; Filters submitted to server!
      </div>
    ) : (
      <GcnEventsFilterForm handleFilterSubmit={handleFilterSubmit} />
    );

  const columns = [
    {
      name: "dateobs",
      label: "Date Observed",
      options: {
        customBodyRenderLite: renderDateObs,
      },
    },
    {
      name: "aliases",
      label: "Aliases",
      options: {
        customBodyRenderLite: renderAliases,
      },
    },
    {
      name: "gcn_tags",
      label: "Event Tags",
      options: {
        customBodyRenderLite: renderGcnTags,
      },
    },
    {
      name: "localization_tags",
      label: "Localization Tags",
      options: {
        customBodyRenderLite: renderLocalizationTags,
      },
    },
    {
      name: "localizations",
      label: "Localizations",
      options: {
        customBodyRenderLite: renderLocalizations,
      },
    },
    {
      name: "gcn_notices",
      label: "GCN Notices",
      options: {
        customBodyRenderLite: renderGcnNotices,
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
    search: false, // Disable search for now (not implemented yet)
    download: false, // Disable download button for now (not implemented yet)
    filter: true,
    customFilterDialogFooter: customFilterDisplay,
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={8} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h5">GCN Events</Typography>
            {gcnEvents ? (
              <StyledEngineProvider injectFirst>
                <ThemeProvider theme={getMuiTheme(theme)}>
                  <MUIDataTable
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
      </Grid>
      <Grid item md={4} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Add a New GcnEvent</Typography>
            <NewGcnEvent />
          </div>
        </Paper>
        <Paper style={{ margin: "16px 0px" }} variant="outlined">
          <div className={classes.paperContent}>
            <Typography variant="h6">Crossmatch</Typography>
            <Crossmatch />
          </div>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default GcnEvents;
