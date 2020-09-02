import React from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import Paper from "@material-ui/core/Paper";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";

const GroupList = ({ title, groups, classes }) => (
  <Paper elevation={1} className={classes.widgetPaperFillSpace}>
    <div className={classes.widgetPaperDiv}>
      <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
      <Typography variant="h6">{title}</Typography>
      <List component="nav" aria-label="main mailbox folders">
        {groups &&
          groups
            .filter((group) => !group.single_user_group)
            .map((group) => (
              <Link to={`/group/${group.id}`} key={group.id}>
                <ListItem key={group.id} button>
                  <ListItemText primary={group.name} />
                </ListItem>
              </Link>
            ))}
      </List>
    </div>
  </Paper>
);

GroupList.propTypes = {
  title: PropTypes.string.isRequired,
  groups: PropTypes.arrayOf(PropTypes.object),
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
};
GroupList.defaultProps = {
  groups: [],
};

export default GroupList;
