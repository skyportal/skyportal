import React from "react";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import makeStyles from "@mui/styles/makeStyles";
import { Link } from "react-router-dom";

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
    <Paper>
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
                <ListItem key={group.id}>
                  <Link
                    to={`/group/${group.id}`}
                    data-testid={`${title}-${group.name}`}
                    color="textSecondary"
                  >
                    {group.name}
                  </Link>
                </ListItem>
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
