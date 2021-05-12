import React from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";
import { makeStyles } from "@material-ui/core/styles";

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
  );
};

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
