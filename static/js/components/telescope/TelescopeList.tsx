import { lazy, Suspense, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { makeStyles } from "tss-react/mui";
import Grid from "@mui/material/Grid";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";
import { IconButton } from "@mui/material";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import ReplayIcon from "@mui/icons-material/Replay";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import SearchIcon from "@mui/icons-material/Search";
import DeleteIcon from "@mui/icons-material/Delete";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import { ToggleButton, ToggleButtonGroup } from "@mui/material";

import { showNotification } from "../../../../baselayer/static/js/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useGetTelescopesQuery,
  useDeleteTelescopeMutation,
} from "../../ducks/telescopes";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import TelescopeTable from "./TelescopeTable";
import Button from "../Button";
import Paper from "../Paper";

// lazy import the TelescopeMap component
const TelescopeMap = lazy(() => import("./TelescopeMap"));

const useStyles = makeStyles()((theme) => ({
  mapContainer: {
    position: "relative",
    width: "100%",
  },
  overlayButtons: {
    position: "absolute",
    bottom: "0.3rem",
    right: "0.3rem",
    display: "flex",
    alignItems: "center",
    gap: "0.2rem",
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

const TelescopeList = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg"));
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const { data: currentUser } = useGetProfileQuery();
  const { data: telescopeList = [], isFetching: loading } =
    useGetTelescopesQuery();
  const [deleteTelescopeMutation] = useDeleteTelescopeMutation();
  const [currentTelescopes, setCurrentTelescopes] = useState<any[]>([]);
  const [displayedTelescopes, setDisplayedTelescopes] = useState(telescopeList);
  const [telescopeToDelete, setTelescopeToDelete] = useState<number | null>(
    null,
  );
  const [selectedTelescope, setSelectedTelescope] = useState<any>(null);
  const [displayTelescopeTable, setDisplayTelescopeTable] = useState(false);
  const [mapKey, setMapKey] = useState(0);

  useEffect(() => {
    setDisplayedTelescopes(telescopeList);
  }, [telescopeList]);

  useEffect(() => {
    if (currentTelescopes?.length) {
      setDisplayedTelescopes(currentTelescopes);
    }
  }, [currentTelescopes]);

  const managePermission =
    currentUser?.permissions?.includes("Manage telescopes") ||
    currentUser?.permissions?.includes("System admin") ||
    false;

  const deleteTelescope = async () => {
    try {
      await deleteTelescopeMutation(telescopeToDelete!).unwrap();
      dispatch(showNotification("Telescope deleted"));
      setTelescopeToDelete(null);
    } catch {
      // error notification handled by the API base query
    }
  };

  const getSpecificIconClasses = (telescope: any) => {
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

  const handleChange = (option: any) => {
    setSelectedTelescope(option);
    if (option) {
      setDisplayedTelescopes([option]);
    } else {
      setDisplayedTelescopes(telescopeList);
      if (currentTelescopes?.length) {
        setCurrentTelescopes([]);
      }
    }
  };

  return (
    <Suspense fallback={<CircularProgress color="secondary" />}>
      <Grid container spacing={5} style={{ position: "relative" }}>
        {!isMobile && (
          <Box
            sx={{
              position: "absolute",
              top: 43,
              left: "50%",
              transform: "translateX(-50%)",
              zIndex: 10,
            }}
          >
            <Paper
              noPadding
              elevation={3}
              sx={{
                borderRadius: "999px",
                px: 0,
                backgroundColor: "rgba(240,242,245,0.7)",
              }}
            >
              <ToggleButtonGroup
                value={displayTelescopeTable}
                exclusive
                onChange={(_e, newView) => {
                  if (newView === null) return;
                  setDisplayTelescopeTable(newView);
                }}
                sx={{
                  height: 34,
                  "& .MuiToggleButton-root": {
                    border: "none",
                    borderRadius: "999px",
                    textTransform: "none",
                    px: 3,
                  },
                }}
              >
                <ToggleButton value={false}>Map</ToggleButton>
                <ToggleButton value={true}>Table</ToggleButton>
              </ToggleButtonGroup>
            </Paper>
          </Box>
        )}
        <Grid
          size={{ lg: 8 }}
          sx={{
            display: {
              xs: "none",
              lg: displayTelescopeTable ? "none" : "block",
            },
          }}
        >
          <Paper>
            <div className={classes.mapContainer}>
              <TelescopeMap
                key={mapKey}
                telescopes={telescopeList}
                onSelectTelescopes={setCurrentTelescopes}
              />
              <div className={classes.overlayButtons}>
                <Tooltip title="Reset view" placement="top">
                  <IconButton
                    size="small"
                    onClick={() => setMapKey((k) => k + 1)}
                  >
                    <ReplayIcon color="action" fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip
                  title={legend()}
                  placement="bottom-end"
                  classes={{ tooltip: classes.tooltip }}
                >
                  <HelpOutlineOutlinedIcon color="action" />
                </Tooltip>
              </div>
            </div>
          </Paper>
        </Grid>
        <Grid
          size={{ xs: 12, lg: displayTelescopeTable ? 12 : 4 }}
          style={{ position: "relative" }}
        >
          {displayTelescopeTable ? (
            <TelescopeTable
              telescopes={telescopeList}
              managePermission={managePermission}
            />
          ) : (
            <Paper
              style={{ maxHeight: "calc(-85px + 100vh)", overflow: "scroll" }}
            >
              <Autocomplete
                color="primary"
                id="telescopes-search-bar"
                classes={{
                  root: (classes as any).root,
                  paper: (classes as any).paper,
                }}
                onChange={(_event, option) => {
                  handleChange(option);
                }}
                value={selectedTelescope}
                options={telescopeList}
                getOptionLabel={(option: any) => option.name || ""}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    variant="outlined"
                    placeholder="Telescope"
                    slotProps={{
                      ...params.slotProps,

                      input: {
                        ...params.slotProps.input,
                        startAdornment: (
                          <InputAdornment position="start">
                            <SearchIcon fontSize="small" />
                          </InputAdornment>
                        ),
                      },
                    }}
                  />
                )}
              />
              <List>
                {displayedTelescopes &&
                  displayedTelescopes.map((telescope: any) => (
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
                        {managePermission && (
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
                          color={
                            telescope.fixed_location ? "primary" : "default"
                          }
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
          )}
        </Grid>
      </Grid>
    </Suspense>
  );
};

export default TelescopeList;
