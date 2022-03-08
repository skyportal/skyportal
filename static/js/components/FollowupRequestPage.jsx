import React from "react";
import { useSelector } from "react-redux";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import FollowupRequestLists from "./FollowupRequestLists";
import FollowupRequestSelectionForm from "./FollowupRequestSelectionForm";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  paperContent: {
    padding: "1rem",
  },
}));

const FollowupRequestPage = () => {
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );
  const { followupRequestList } = useSelector(
    (state) => state.followup_requests
  );
  const classes = useStyles();

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Followup Requests</Typography>
            <FollowupRequestLists
              followupRequests={followupRequestList}
              instrumentList={instrumentList}
              instrumentFormParams={instrumentFormParams}
              showObject
            />
          </div>
        </Paper>
      </Grid>
      <Grid item md={6} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Query Followup Requests</Typography>
            <FollowupRequestSelectionForm />
          </div>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default FollowupRequestPage;
