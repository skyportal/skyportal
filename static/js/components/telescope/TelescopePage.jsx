import React, { lazy, Suspense, useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import * as telescopesActions from "../../ducks/telescopes";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import { Link } from "react-router-dom";
import Button from "../Button";
import DeleteIcon from "@mui/icons-material/Delete";
import Chip from "@mui/material/Chip";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import { showNotification } from "../../../../baselayer/static/js/components/Notifications";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import SearchIcon from "@mui/icons-material/Search";
import Typography from "@mui/material/Typography";

// lazy import the TelescopeMap component
const TelescopeMap = lazy(() => import("./TelescopeMap"));

const useStyles = makeStyles((theme) => ({
  paperContent: {
    padding: "0.5rem",
  },
  help: {
    textAlign: "right",
  },
  tooltip: {
    padding: "1rem",
    maxWidth: "60rem",
    fontSize: "1rem",
  },
  tooltipContent: {
    display: "flex",
    flexDirection: "column",
    gap: "0.7rem",
  },
  legend: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
  },
  baseIcon: {
    minHeight: "1rem",
    minWidth: "1rem",
    borderRadius: "50%",
    margin: "0.25rem 0.75rem",
  },
  canObserveFixed: {
    backgroundColor: "#0c1445",
  },
  cannotObserveFixed: {
    backgroundColor: "#f9d71c",
  },
  cannotObserveNonFixed: {
    backgroundColor: "#5ca9d6",
    borderRadius: "0",
  },
  listItem: {
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    borderBottom: `1px solid ${theme.palette.divider}`,
    padding: "0.8rem 0",
  },
  header: {
    display: "flex",
    alignItems: "center",
    marginBottom: "0.5rem",
    gap: "0.5rem",
    textAlign: "center",
  },
  info: {
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    alignItems: "center",
  },
  date: {
    fontSize: "1rem",
    color: "#666",
    display: "flex",
    flexDirection: "column",
  },
  telescopeDelete: {
    position: "absolute",
    right: 0,
    top: 0,
  },
}));

const TelescopePage = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const loading = useSelector((state) => state.telescopes.loading);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { currentTelescopes } = useSelector((state) => state.telescopes);
  const [displayedTelescopes, setDisplayedTelescopes] = useState(telescopeList);
  const [telescopeToDelete, setTelescopeToDelete] = useState(null);
  const [selectedTelescope, setSelectedTelescope] = useState(null);

  useEffect(() => {
    setDisplayedTelescopes(telescopeList);
  }, [telescopeList]);

  useEffect(() => {
    if (currentTelescopes?.length) {
      setDisplayedTelescopes(currentTelescopes);
    }
  }, [currentTelescopes]);

  const permission =
    currentUser.permissions?.includes("Delete telescope") ||
    currentUser.permissions?.includes("System admin");

  const deleteTelescope = () => {
    dispatch(telescopesActions.deleteTelescope(telescopeToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Telescope deleted"));
          setTelescopeToDelete(null);
        }
      },
    );
  };

  const getSpecificIconClasses = (telescope) => {
    if (!telescope.fixed_location) return classes.cannotObserveNonFixed;
    if (telescope.is_night_astronomical) return classes.canObserveFixed;
    return classes.cannotObserveFixed;
  };

  const legend = () => (
    <div className={classes.tooltipContent}>
      <div className={classes.legend}>
        <p className={`${classes.baseIcon} ${classes.cannotObserveFixed}`} />
        Daytime
      </div>
      <div className={classes.legend}>
        <p className={`${classes.baseIcon} ${classes.canObserveFixed}`} />
        Nighttime
      </div>
      <div className={classes.legend}>
        <p className={`${classes.baseIcon} ${classes.cannotObserveNonFixed}`} />
        Networks and Space-based Instruments
      </div>
    </div>
  );

  const handleChange = (option) => {
    setSelectedTelescope(option);
    if (option) {
      setDisplayedTelescopes([option]);
    } else {
      setDisplayedTelescopes(telescopeList);
      if (currentTelescopes?.length) {
        dispatch({
          type: "skyportal/CURRENT_TELESCOPES",
          data: { currentTelescopes: [] },
        });
      }
    }
  };

  const SearchBar = () => (
    <Autocomplete
      color="primary"
      id="telescopes-search-bar"
      classes={{ root: classes.root, paper: classes.paper }}
      onChange={(event, option) => {
        handleChange(option);
      }}
      value={selectedTelescope}
      options={telescopeList}
      getOptionLabel={(option) => option.name || ""}
      renderInput={(params) => (
        <TextField
          {...params}
          variant="outlined"
          placeholder="Telescope"
          InputProps={{
            ...params.InputProps,
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      )}
    />
  );

  return (
    <Suspense
      fallback={
        <div>
          <CircularProgress color="secondary" />
        </div>
      }
    >
      <Grid container spacing={3}>
        <Grid item lg={8} sx={{ display: { xs: "none", lg: "block" } }}>
          <Paper className={classes.paperContent}>
            <TelescopeMap telescopes={telescopeList} />
            <div className={classes.help}>
              <Tooltip
                title={legend()}
                placement="bottom-end"
                classes={{ tooltip: classes.tooltip }}
              >
                <HelpOutlineOutlinedIcon />
              </Tooltip>
            </div>
          </Paper>
        </Grid>
        <Grid item xs={12} lg={4}>
          <Paper
            className={classes.paperContent}
            style={{ maxHeight: "calc(-85px + 100vh)", overflow: "scroll" }}
          >
            <SearchBar />
            <List>
              {displayedTelescopes &&
                displayedTelescopes.map((telescope) => (
                  <ListItem
                    id={`${telescope.name}_info`}
                    className={classes.listItem}
                    key={`${telescope.id}_list_item`}
                  >
                    <div className={classes.header}>
                      <span
                        className={`${
                          classes.baseIcon
                        } ${getSpecificIconClasses(telescope)}`}
                      />
                      <Link to={`/telescope/${telescope.id}`} role="link">
                        <Typography
                          variant="h2"
                          sx={{
                            fontWeight: 400,
                            fontSize: {
                              xs: "1.2rem",
                              sm: "1.5rem",
                            },
                          }}
                        >
                          {telescope.name} ({telescope.nickname})
                        </Typography>
                      </Link>
                      {permission && (
                        <div style={{ minWidth: "2.5rem" }}>
                          <Button
                            id="delete_button"
                            classes={{ root: classes.telescopeDelete }}
                            onClick={() => setTelescopeToDelete(telescope.id)}
                          >
                            <DeleteIcon />
                          </Button>
                        </div>
                      )}
                    </div>
                    {telescope.fixed_location && (
                      <>
                        <div className={classes.date}>
                          {telescope.morning && (
                            <i>
                              Next Sunrise (Astronomical):{" "}
                              {telescope.morning.slice(8, -4)} UTC
                            </i>
                          )}
                          {telescope.evening && (
                            <i>
                              Next Sunset (Astronomical):{" "}
                              {telescope.evening.slice(8, -4)} UTC
                            </i>
                          )}
                        </div>
                        <div>
                          <b>Location:</b> {telescope.lat?.toFixed(4)},{" "}
                          {telescope.lon?.toFixed(4)}
                        </div>
                        <div>
                          <b>Elevation:</b> {telescope.elevation?.toFixed(1)}
                        </div>
                      </>
                    )}
                    <div>
                      <b>Diameter:</b> {telescope.diameter?.toFixed(1)}
                    </div>
                    <div>
                      <b>Robotic:</b>{" "}
                      <Chip
                        label={telescope.robotic ? "Yes" : "No"}
                        size="small"
                        color={telescope.robotic ? "primary" : "default"}
                      />
                    </div>
                    <div>
                      <b>Fixed Location:</b>{" "}
                      <Chip
                        label={telescope.fixed_location ? "Yes" : "No"}
                        size="small"
                        color={telescope.fixed_location ? "primary" : "default"}
                      />
                    </div>
                    {telescope.skycam_link && (
                      <a href={telescope.skycam_link}>skycam link</a>
                    )}
                  </ListItem>
                ))}
              {loading && (
                <div style={{ textAlign: "center", paddingTop: "1rem" }}>
                  <CircularProgress size={30} />
                </div>
              )}
            </List>
            <ConfirmDeletionDialog
              deleteFunction={deleteTelescope}
              dialogOpen={telescopeToDelete !== null}
              closeDialog={() => setTelescopeToDelete(null)}
              resourceName="telescope"
            />
          </Paper>
        </Grid>
      </Grid>
    </Suspense>
  );
};

export default TelescopePage;
