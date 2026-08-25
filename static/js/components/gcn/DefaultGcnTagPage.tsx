import { useGetProfileQuery } from "../../ducks/profile";
import { makeStyles } from "tss-react/mui";
import NewDefaultGcnTag from "./NewDefaultGcnTag";
import DefaultGcnTagTable from "./DefaultGcnTagTable";

import { useGetDefaultGcnTagsQuery } from "../../ducks/default_gcn_tags";

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
  const { data: defaultGcnTagList } = useGetDefaultGcnTagsQuery();
  const { data: currentUser } = useGetProfileQuery();

  const permission =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage GCNs");

  const tableProps: any = {
    default_gcn_tags: defaultGcnTagList,
    deletePermission: permission,
  };
  return <DefaultGcnTagTable {...tableProps} />;
};

const DefaultGcnTagPage = () => {
  const { data: currentUser } = useGetProfileQuery();
  const { classes } = useStyles();

  const permission =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage GCNs");

  return (
    <div className={classes.root}>
      <DefaultGcnTags />
      {permission && <NewDefaultGcnTag />}
    </div>
  );
};

export default DefaultGcnTagPage;
