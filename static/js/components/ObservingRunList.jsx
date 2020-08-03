import React from 'react';
import { useSelector } from 'react-redux';
import PropTypes from 'prop-types';

import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import Typography from '@material-ui/core/Typography';
import { makeStyles } from "@material-ui/core/styles";
import { observingRunTitle } from "./AssignmentForm";

const useStyles = makeStyles((theme) => ({
  root: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: theme.palette.background.paper,
  },
}));

const ListItemLink = ({ href }) => (
  <ListItem button component="a" href={href} />
);

function SimpleList({ observingRuns }) {
  const classes = useStyles();
  const { instrumentList } = useSelector((state) => (state.instruments));
  const { telescopeList } = useSelector((state) => (state.telescopes));
  const groups = useSelector((state) => (state.groups.all));

  return (
    <div className={classes.root}>
      <List component="nav">
        {
          observingRuns.map((run) => (
            <ListItemLink href={`/run/${run.id}`} key={`run_${run.id}`}>
              <ListItemText
                primary={observingRunTitle(run, instrumentList, telescopeList, groups)}
              />
            </ListItemLink>
          ))
        }
      </List>
    </div>
  );
}

const ObservingRunList = () => {
  const { observingRunList } = useSelector((state) => state.observingRuns);
  return (
    <div>
      <Typography variant="h6">
        List of Observing Runs in Skyportal
      </Typography>
      <SimpleList observingRuns={observingRunList} />
    </div>
  );
};


SimpleList.propTypes = {
  observingRuns: PropTypes.arrayOf(
    PropTypes.shape({
      instrument_id: PropTypes.number,
      pi: PropTypes.string,
      calendar_date: PropTypes.string,
      id: PropTypes.number
    })
  ).isRequired
};

ListItemLink.propTypes = {
  href: PropTypes.string.isRequired
}

export default ObservingRunList;
