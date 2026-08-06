import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Paper from "@mui/material/Paper";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";

import { useGetFilterQuery } from "../../ducks/filter";
import { useGetBrokersQuery } from "../../ducks/brokers";
import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
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

// A filter attached to a broker gets the same builder the
// /brokers/:brokerId/filter/:fid route renders; anything else has no plugins.
const FilterPlugins = ({ group }: FilterPluginsProps) => {
  const { classes } = useStyles();
  const { fid } = useParams();
  const { data: filter } = useGetFilterQuery(fid ?? "", { skip: !fid }) as any;
  const [filterOrigin, setFilterOrigin] = useState<any>(null);
  console.log("filter", filter, "filterOrigin", filterOrigin);
  useEffect(() => {
    if (filterOrigin || !filter) {
      return;
    }
    // Determine filter origin
    if (filter?.altdata?.boom) {
      setFilterOrigin("boom");
    } else {
      // If the filter has no altdata, we want it to default to a BOOM filter.
      // This allows
      setFilterOrigin("boom");
    }
  }, [fid, filter]);

  // The boom filter builder now uses SkyPortal's per-broker endpoints
  // (/api/brokers/{id}/filters), so it needs the BOOM broker targeted.
  const { data: brokers } = useGetBrokersQuery();
  const boomBrokerId = (brokers || []).find(
    (b: any) => b.broker_classname === "BOOMBROKER" && b.active,
  )?.id;

  if (!filter || filterOrigin === null) {
    return (
      <Paper className={classes.paperDiv}>
        <CircularProgress />
      </Paper>
    );
  }

  if (filterOrigin === "boom") {
    if (boomBrokerId == null) {
      return (
        <Paper className={classes.paperDiv}>
          <CircularProgress />
        </Paper>
      );
    }
    setBrokerFilterTarget(boomBrokerId);
    return <BoomFilterPlugins group={group} />;
  } else {
    return (
      <Paper className={classes.paperDiv}>
        <div>Unable to determine filter type.</div>
      </Paper>
    );
  }
};

export default FilterPlugins;
