import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import {
  makeStyles,
  createMuiTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";
import Chip from "@material-ui/core/Chip";
import Button from "@material-ui/core/Button";

import MUIDataTable from "mui-datatables";

import * as gcnEventsActions from "../ducks/gcnEvents";

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
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createMuiTheme({
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

const GcnEvents = () => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();
  const gcnEvents = useSelector((state) => state.gcnEvents);

  useEffect(() => {
    dispatch(gcnEventsActions.fetchGcnEvents());
  }, [dispatch]);

  const renderTags = (tags) =>
    tags?.map((tag) => (
      <Chip size="small" key={tag} label={tag} className={classes.eventTags} />
    ));

  const renderGcnNotices = (dataIndex) => (
    <ul>
      {gcnEvents[dataIndex]?.gcn_notices?.map((gcnNotice) => (
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
      {gcnEvents[dataIndex]?.localizations?.map((loc) => (
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
    <Link to={`/gcn_events/${gcnEvents[dataIndex]?.dateobs}`}>
      <Button color="primary">{gcnEvents[dataIndex]?.dateobs}</Button>
    </Link>
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
      name: "tags",
      label: "Tags",
      options: {
        customBodyRender: renderTags,
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
    search: true,
    selectableRows: "none",
    elevation: 0,
  };

  return (
    <div>
      <Typography variant="h5">GCN Events</Typography>
      {gcnEvents ? (
        <Paper className={classes.container}>
          <MuiThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              data={gcnEvents}
              options={options}
              columns={columns}
            />
          </MuiThemeProvider>
        </Paper>
      ) : (
        <CircularProgress />
      )}
    </div>
  );
};

export default GcnEvents;
