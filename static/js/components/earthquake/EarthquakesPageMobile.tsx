import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";

import { useAppSelector } from "../../types/hooks";
import NewEarthquake from "./NewEarthquake";

const useStyles = makeStyles()((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paperContent: {
    padding: "1rem",
  },
}));

const textStyles = makeStyles()(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

export function earthquakeTitle(earthquake: any) {
  if (!earthquake?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${earthquake?.nickname}`;
  return result;
}

export function earthquakeInfo(earthquake: any) {
  if (!earthquake?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const array = [
    ...(earthquake?.lat ? [`Latitude: ${earthquake.lat}`] : []),
    ...(earthquake?.lon ? [`Longitude: ${earthquake.lon}`] : []),
    ...(earthquake?.elevation ? [`Elevation: ${earthquake.elevation}`] : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = "( " + array.join(" / ") + " )";

  return result;
}

interface EarthquakeListProps {
  earthquakes: any[];
}

const EarthquakeList = ({ earthquakes }: EarthquakeListProps) => {
  const { classes } = useStyles();
  const { classes: textClasses } = textStyles();

  return (
    <div className={classes.root}>
      <List component="nav">
        {earthquakes?.map((earthquake) => (
          <ListItem key={earthquake.id}>
            <ListItemText
              primary={earthquakeTitle(earthquake)}
              secondary={earthquakeInfo(earthquake)}
              classes={textClasses as any}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const EarthquakePage = () => {
  const { earthquakeList } = useAppSelector(
    (state) => state.earthquakes,
  ) as any;
  const currentUser = useAppSelector((state) => state.profile);

  const { classes } = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid size={{ md: 6, sm: 12 }}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Earthquakes</Typography>
            <EarthquakeList earthquakes={earthquakeList} />
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("Manage allocations") && (
        <Grid size={{ md: 6, sm: 12 }}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add a New Earthquake</Typography>
              <NewEarthquake />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

export default EarthquakePage;
