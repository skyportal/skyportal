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
import makeStyles from "@mui/styles/makeStyles";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import InfoIcon from "@mui/icons-material/Info";

import MUIDataTable from "mui-datatables";

import { filterOutEmptyValues } from "../../API";
import * as earthquakeActions from "../../ducks/earthquake";
import Spinner from "../Spinner";
import EarthquakesFilterForm from "./EarthquakesFilterForm";

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

const defaultNumPerPage = 10;

const Earthquake = () => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();
  const earthquakes = useSelector((state) => state.earthquakes);
  const [filterFormSubmitted, setFilterFormSubmitted] = useState(false);

  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  useEffect(() => {
    dispatch(earthquakeActions.fetchEarthquakes());
  }, [dispatch]);

  if (!earthquakes) {
    return <p>No earthquakes available...</p>;
  }

  const { events, totalMatches } = earthquakes;

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
    await dispatch(earthquakeActions.fetchEarthquakes(params));
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
    }
    // Save state for future
    setFetchParams(params);
    await dispatch(earthquakeActions.fetchEarthquakes(params));
  };

  const handleTableSorting = async (sortData) => {
    const params = {
      ...fetchParams,
      pageNumber: 1,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchParams(params);
    await dispatch(earthquakeActions.fetchEarthquakes(params));
  };

  const handleFilterSubmit = async (formData) => {
    const data = filterOutEmptyValues(formData);

    handleTableFilter(1, defaultNumPerPage, data);
    setFilterFormSubmitted(true);
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

  const renderNotices = (dataIndex) => (
    <ul>
      {events[dataIndex]?.notices?.map((gcnNotice) => (
        <li key={gcnNotice.id}>
          {["date", "magnitude", "lat", "lon", "depth", "country"].map(
            (attr) => (
              <p key={attr}>
                {attr}: {gcnNotice[attr]}
              </p>
            ),
          )}
        </li>
      ))}
    </ul>
  );

  const renderEvent = (dataIndex) => (
    <Link to={`/earthquakes/${events[dataIndex]?.event_id}`}>
      <Button className={classes.gcnEventLink}>
        {events[dataIndex]?.event_id}
      </Button>
    </Link>
  );

  const customFilterDisplay = () =>
    filterFormSubmitted ? (
      <div className={classes.filterAlert}>
        <InfoIcon /> &nbsp; Filters submitted to server!
      </div>
    ) : (
      <EarthquakesFilterForm handleFilterSubmit={handleFilterSubmit} />
    );

  const columns = [
    {
      name: "event_id",
      label: "ID",
      options: {
        customBodyRenderLite: renderEvent,
      },
    },
    {
      name: "notices",
      label: "Notices",
      options: {
        customBodyRenderLite: renderNotices,
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
      <Grid item md={12} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h5">Earthquake Events</Typography>
            {earthquakes ? (
              <StyledEngineProvider injectFirst>
                <ThemeProvider theme={getMuiTheme(theme)}>
                  <MUIDataTable
                    data={earthquakes.events}
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
    </Grid>
  );
};

export default Earthquake;
