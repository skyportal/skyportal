import React, { useEffect } from "react";
import { makeStyles } from "tss-react/mui";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import NewDefaultGcnTag from "./NewDefaultGcnTag";
import DefaultGcnTagTable from "./DefaultGcnTagTable";

import * as defaultGcnTagsActions from "../../ducks/default_gcn_tags";

const useStyles = makeStyles()((theme) => ({
  root: {
    width: "100%",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line" as const,
  },
  hover: {
    "&:hover": {
      textDecoration: "underline",
    },
    color: theme.palette.mode === "dark" ? "#fafafa !important" : undefined,
  },
}));

const DefaultGcnTags = () => {
  const dispatch = useAppDispatch();

  const default_gcn_tags = useAppSelector((state) => state.default_gcn_tags);
  const currentUser = useAppSelector((state) => state.profile);

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage GCNs");

  useEffect(() => {
    dispatch(defaultGcnTagsActions.fetchDefaultGcnTags());
  }, [dispatch]);

  const tableProps: any = {
    default_gcn_tags: default_gcn_tags.defaultGcnTagList,
    deletePermission: permission,
  };
  return <DefaultGcnTagTable {...tableProps} />;
};

const DefaultGcnTagPage = () => {
  const currentUser = useAppSelector((state) => state.profile);
  const { classes } = useStyles();

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
