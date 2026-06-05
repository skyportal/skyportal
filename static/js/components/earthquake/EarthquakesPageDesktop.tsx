import { lazy, Suspense, useState } from "react";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import NewEarthquake from "./NewEarthquake";
import EarthquakeInfo from "./EarthquakeInfo";
import Spinner from "../Spinner";
import { useAppSelector } from "../../types/hooks";
import { useGetEarthquakesQuery } from "../../ducks/earthquake";
// lazy import the EarthquakeMap component
const EarthquakeMap = lazy(() => import("./EarthquakeMap"));

const useStyles = makeStyles()(() => ({
  paperContent: {
    padding: "1rem",
  },
  menu: {
    display: "flex",
    direction: "row" as any,
    justifyContent: "space-around",
    alignItems: "center",
    marginBottom: "1rem",
  },
  selectedMenu: {
    height: "3rem",
    backgroundColor: "lightblue",
    fontSize: "1.2rem",
  },
  nonSelectedMenu: {
    height: "3rem",
    fontSize: "1.2rem",
  },
}));

const EarthquakePage = () => {
  const { classes } = useStyles();
  const currentUser = useAppSelector((state) => state.profile);
  const { data: earthquakes } = useGetEarthquakesQuery();
  const [currentEarthquakeMenu, setCurrentEarthquakeMenu] =
    useState("Earthquake List");

  if (!earthquakes) return <Spinner />;

  function setSelectedMenu(currentSelectedEarthquakeMenu: string) {
    setCurrentEarthquakeMenu(currentSelectedEarthquakeMenu);
  }

  function isMenuSelected(menu: string) {
    return menu === currentEarthquakeMenu
      ? classes.selectedMenu
      : classes.nonSelectedMenu;
  }

  return (
    <Suspense fallback={<CircularProgress color="secondary" />}>
      <Grid container spacing={3}>
        <Grid size={{ md: 8, sm: 12 }}>
          <Paper className={classes.paperContent}>
            <EarthquakeMap
              earthquakes={(earthquakes as any).events}
              onSelectEarthquakes={() => setSelectedMenu("Earthquake List")}
            />
          </Paper>
        </Grid>
        <Grid size={{ md: 4, sm: 12 }}>
          <Paper className={classes.menu}>
            <Button
              onClick={() => setSelectedMenu("Earthquake List")}
              className={isMenuSelected("Earthquake List")}
            >
              Earthquake List
            </Button>
            {currentUser.permissions?.includes("Manage allocations") && (
              <Button
                onClick={() => setSelectedMenu("New Earthquake")}
                className={isMenuSelected("New Earthquake")}
              >
                New Earthquake
              </Button>
            )}
          </Paper>
          <Paper className={classes.paperContent}>
            {currentEarthquakeMenu === "Earthquake List" ? (
              <EarthquakeInfo />
            ) : (
              currentUser.permissions?.includes("Manage allocations") && (
                <NewEarthquake />
              )
            )}
          </Paper>
        </Grid>
      </Grid>
    </Suspense>
  );
};

export default EarthquakePage;
