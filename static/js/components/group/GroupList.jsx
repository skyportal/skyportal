import React from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import Paper from "@mui/material/Paper";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import makeStyles from "@mui/styles/makeStyles";

const useStyles = makeStyles(() => ({
  listContainer: {
    overflowX: "hidden",
    overflowY: "scroll",
    height: "calc(95% - 1.25rem);",
  },
  flex: {
    display: "flex",
    flexFlow: "column nowrap",
  },
}));

const GroupList = ({ title, groups, classes }) => {
  const styles = useStyles();

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={`${classes.widgetPaperDiv} ${styles.flex}`}>
        <div>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <Typography variant="h6">{title}</Typography>
        </div>
        <List
          component="nav"
          aria-label="main mailbox folders"
          className={styles.listContainer}
        >
          {groups &&
            groups
              .filter((group) => !group.single_user_group)
              .map((group) => (
                <Link to={`/group/${group.id}`} key={group.id}>
                  <ListItem
                    key={group.id}
                    button
                    data-testid={`${title}-${group.name}`}
                  >
                    <ListItemText primary={group.name} />
                  </ListItem>
                </Link>
              ))}
        </List>
      </div>
    </Paper>
  );
};

GroupList.propTypes = {
  title: PropTypes.string.isRequired,
  groups: PropTypes.arrayOf(PropTypes.object), // eslint-disable-line react/forbid-prop-types
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
