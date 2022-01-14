import React from "react";
import { useSelector } from "react-redux";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import PropTypes from "prop-types";
import CircularProgress from "@material-ui/core/CircularProgress";
import NewAllocation from "./NewAllocation";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paperContent: {
    padding: "1rem",
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

export function allocationTitle(allocation, instrumentList, telescopeList) {
  const { instrument_id } = allocation;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!(allocation?.start_date && instrument?.name && telescope?.name)) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${instrument?.name}/${telescope?.nickname}`;

  return result;
}

export function allocationInfo(allocation, groups) {
  const group = groups?.filter((g) => g.id === allocation.group_id)[0];

  if (!allocation?.start_date) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  let result = `${allocation?.start_date}-${allocation?.end_date}`;

  if (allocation?.pi || group?.name) {
    result += " (";
    if (allocation?.pi) {
      result += `PI: ${allocation.pi}`;
    }
    if (group?.name) {
      result += ` / Group: ${group?.name}`;
    }
    result += ")";
  }

  return result;
}

const AllocationList = ({ allocations }) => {
  const classes = useStyles();
  const textClasses = textStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  return (
    <div className={classes.root}>
      <List component="nav">
        {allocations?.map((allocation) => (
          <ListItem button key={allocation.id}>
            <ListItemText
              primary={allocationTitle(
                allocation,
                instrumentList,
                telescopeList
              )}
              secondary={allocationInfo(allocation, groups)}
              classes={textClasses}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const AllocationPage = () => {
  const { allocationList } = useSelector((state) => state.allocations);
  const classes = useStyles();

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Allocations</Typography>
            <AllocationList allocations={allocationList} />
          </div>
        </Paper>
      </Grid>
      <Grid item md={6} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Add a New Allocation</Typography>
            <NewAllocation />
          </div>
        </Paper>
      </Grid>
    </Grid>
  );
};

AllocationList.propTypes = {
  allocations: PropTypes.arrayOf(PropTypes.any).isRequired,
};

export default AllocationPage;
