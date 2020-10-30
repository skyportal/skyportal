import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import { makeStyles } from "@material-ui/core/styles";

import Typography from "@material-ui/core/Typography";
import CircularProgress from "@material-ui/core/CircularProgress";
import SourceTable from "./SourceTable";

import * as sourcesActions from "../ducks/sources";

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  source: {},
  commentListContainer: {
    height: "15rem",
    overflowY: "scroll",
    padding: "0.5rem 0",
  },
  tableGrid: {
    width: "100%",
  },
}));

const GroupSources = ({ route }) => {
  const dispatch = useDispatch();
  const sources = useSelector((state) => state.sources.groupSources);
  const groups = useSelector((state) => state.groups.userAccessible);
  const classes = useStyles();

  // Load the group sources
  useEffect(() => {
    dispatch(
      sourcesActions.fetchGroupSources({
        group_ids: [route.id],
        includeRequested: true,
      })
    );
  }, [route.id, dispatch]);

  if (!sources) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  const groupID = parseInt(route.id, 10);

  const groupName = groups.filter((g) => g.id === groupID)[0]?.name || "";

  if (sources.length === 0) {
    return (
      <div className={classes.source}>
        <Typography variant="h4" gutterBottom align="center">
          {`${groupName} sources`}
        </Typography>
        <br />
        <Typography align="center">
          No sources have been saved to this group yet.
        </Typography>
      </div>
    );
  }

  const savedSources = sources.filter((source) => {
    const matchingGroup = source.groups.filter((g) => g.id === groupID)[0];
    return matchingGroup?.active;
  });
  const pendingSources = sources.filter((source) => {
    const matchingGroup = source.groups.filter((g) => g.id === groupID)[0];
    return matchingGroup?.requested;
  });

  return (
    <div className={classes.source}>
      <Typography variant="h4" gutterBottom align="center">
        {`${groupName} sources`}
      </Typography>
      <br />
      {savedSources && (
        <SourceTable
          sources={savedSources}
          title="Saved"
          sourceStatus="saved"
          groupID={groupID}
        />
      )}
      <br />
      <br />
      {pendingSources && (
        <SourceTable
          sources={pendingSources}
          title="Requested to save"
          sourceStatus="requested"
          groupID={groupID}
        />
      )}
    </div>
  );
};

GroupSources.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default GroupSources;
