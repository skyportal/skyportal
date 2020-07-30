import React from 'react';
import { useSelector } from 'react-redux';

import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import { makeStyles } from "@material-ui/core/styles";

import { observingRunTitle } from "./AssignmentForm";

const useStyles = makeStyles((theme) => ({
  root: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: theme.palette.background.paper,
  },
}));

function ListItemLink(props) {
  return <ListItem button component="a" {...props} />;
}

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
            <ListItemLink href={`/run/${run.id}`}>
              <ListItemText primary={observingRunTitle(run, instrumentList, telescopeList, groups)}/>
            </ListItemLink>
          ))
        }
      </List>
    </div>
  );
}

const ObservingRunList = () => {
  const { observingRunList } = useSelector((state) => state.observingRuns);
  return <SimpleList observingRuns={observingRunList}/>;
};


export default ObservingRunList;
