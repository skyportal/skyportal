import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import NewDefaultGcnTag from "./NewDefaultGcnTag";
import DefaultGcnTagTable from "./DefaultGcnTagTable";

import * as defaultGcnTagsActions from "../ducks/default_gcn_tags";

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
  hover: {
    "&:hover": {
      textDecoration: "underline",
    },
    color: theme.palette.mode === "dark" ? "#fafafa !important" : null,
  },
}));

const DefaultGcnTags = () => {
  const dispatch = useDispatch();
  const classes = useStyles();

  const default_gcn_tags = useSelector((state) => state.default_gcn_tags);
  const currentUser = useSelector((state) => state.profile);

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage GCNs");

  useEffect(() => {
    dispatch(defaultGcnTagsActions.fetchDefaultGcnTags());
  }, [dispatch]);

  return (
    <div className={classes.paper}>
      <DefaultGcnTagTable
        default_gcn_tags={default_gcn_tags.defaultGcnTagList}
        deletePermission={permission}
      />
    </div>
  );
};

const DefaultGcnTagPage = () => {
  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage GCNs");

  return (
    <Grid container spacing={3}>
      <Grid item md={permission ? 8 : 12} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <DefaultGcnTags />
          </div>
        </Paper>
        {permission && (
          <>
            <Paper>
              <div className={classes.paperContent}>
                <Typography variant="h6">Add a New Default GcnTag</Typography>
                <NewDefaultGcnTag />
              </div>
            </Paper>
          </>
        )}
      </Grid>
    </Grid>
  );
};

export default DefaultGcnTagPage;
