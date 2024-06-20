import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import makeStyles from "@mui/styles/makeStyles";
import NewDefaultGcnTag from "./NewDefaultGcnTag";
import DefaultGcnTagTable from "./DefaultGcnTagTable";

import * as defaultGcnTagsActions from "../../ducks/default_gcn_tags";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
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

  const default_gcn_tags = useSelector((state) => state.default_gcn_tags);
  const currentUser = useSelector((state) => state.profile);

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage GCNs");

  useEffect(() => {
    dispatch(defaultGcnTagsActions.fetchDefaultGcnTags());
  }, [dispatch]);

  return (
    <DefaultGcnTagTable
      default_gcn_tags={default_gcn_tags.defaultGcnTagList}
      deletePermission={permission}
    />
  );
};

const DefaultGcnTagPage = () => {
  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage GCNs");

  return (
    <div className={classes.root}>
      <DefaultGcnTags />
      {permission && <NewDefaultGcnTag />}
    </div>
  );
};

export default DefaultGcnTagPage;
