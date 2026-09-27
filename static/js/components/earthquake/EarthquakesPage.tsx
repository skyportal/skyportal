import { lazy, Suspense, useState } from "react";
import Grid from "@mui/material/Grid";
import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import Typography from "@mui/material/Typography";

import { useGetProfileQuery } from "../../ducks/profile";
import { useGetEarthquakesQuery } from "../../ducks/earthquake";
import Button from "../Button";
import NewEarthquake from "./NewEarthquake";
import EarthquakeList from "./EarthquakeList";
import Paper from "../Paper";
import Spinner from "../Spinner";

const EarthquakeMap = lazy(() => import("./EarthquakeMap"));

const panelStyles = (isSelected: boolean) => ({
  color: "text.secondary",
  width: "50%",
  transition: "background-color 0.3s ease",
  boxShadow: "0 -4px 8px -4px rgba(0, 0, 0, 0.2)",
  borderBottomRightRadius: 0,
  borderBottomLeftRadius: 0,
  "&:hover": {
    boxShadow: isSelected
      ? "0 -4px 8px -4px rgba(0, 0, 0, 0.2)"
      : "0 -3px 8px -5px rgba(0, 0, 0, 0.2)",
    backgroundColor: isSelected
      ? "background.paper"
      : "action.disabledBackground",
  },
  ...(isSelected && {
    zIndex: 3,
    backgroundColor: "background.paper",
    borderBottom: "none",
  }),
});

const EarthquakesPage = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg"));
  const { data: currentUser } = useGetProfileQuery();
  const canManage = currentUser?.permissions?.includes("Manage allocations");
  const { data } = useGetEarthquakesQuery();
  const earthquakes = data?.events ?? [];
  const [newEarthquake, setNewEarthquake] = useState(false);

  return (
    <Suspense fallback={<Spinner />}>
      <Grid container spacing={3}>
        <Grid size={{ lg: 8, md: 6, sm: 12 }}>
          <Paper>
            {isMobile ? (
              <>
                <Typography variant="h6" sx={{ fontWeight: "500" }}>
                  List of Earthquakes
                </Typography>
                <EarthquakeList earthquakes={earthquakes} isMobile />
              </>
            ) : (
              <EarthquakeMap earthquakes={earthquakes} />
            )}
          </Paper>
        </Grid>
        {(!isMobile || canManage) && (
          <Grid size={{ lg: 4, md: 6, sm: 12 }}>
            {!isMobile && canManage && (
              <Box>
                <Button
                  secondary
                  onClick={() => setNewEarthquake(false)}
                  sx={panelStyles(!newEarthquake)}
                >
                  Earthquakes
                </Button>
                <Button
                  secondary
                  onClick={() => setNewEarthquake(true)}
                  sx={panelStyles(newEarthquake)}
                >
                  <AddIcon />
                </Button>
              </Box>
            )}
            <Paper>
              {isMobile && (
                <Typography variant="h6" sx={{ fontWeight: "500" }}>
                  Add a New Earthquake
                </Typography>
              )}
              {canManage && (newEarthquake || isMobile) ? (
                <NewEarthquake />
              ) : (
                <EarthquakeList earthquakes={earthquakes} />
              )}
            </Paper>
          </Grid>
        )}
      </Grid>
    </Suspense>
  );
};

export default EarthquakesPage;
