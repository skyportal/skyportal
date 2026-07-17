import { useParams } from "react-router-dom";
import Paper from "@mui/material/Paper";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";

import { useGetFilterQuery } from "../../ducks/filter";

import BoomFilterPlugins from "./boom/BoomFilterPlugins";

interface FilterPluginsProps {
  group?: any;
}

const useStyles = makeStyles()(() => ({
  paperDiv: {
    padding: "1rem",
    height: "100%",
  },
}));

const FilterPlugins = ({ group }: FilterPluginsProps) => {
  const { classes } = useStyles();

  const { fid } = useParams();

  const { data: filter } = useGetFilterQuery(fid ?? "", {
    skip: !fid,
  }) as any;

  if (!filter) {
    return (
      <Paper className={classes.paperDiv}>
        <CircularProgress />
      </Paper>
    );
  }

  return <BoomFilterPlugins group={group} />;
};

export default FilterPlugins;
