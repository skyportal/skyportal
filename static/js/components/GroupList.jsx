import React from "react";
import PropTypes from "prop-types";
import Paper from "@material-ui/core/Paper";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Typography from "@material-ui/core/Typography";

const GroupList = ({ title, groups }) => (
  <Paper elevation={1} height="100%">
    <div style={{ padding: "1rem" }}>
      <Typography variant="h6">{title}</Typography>

      <List component="nav" aria-label="main mailbox folders">
        {groups &&
          groups
            .filter((group) => !group.single_user_group)
            .map((group) => (
              <ListItem
                key={group.id}
                button
                component="a"
                href={`/group/${group.id}`}
              >
                <ListItemText primary={group.name} />
              </ListItem>
            ))}
      </List>
    </div>
  </Paper>
);

GroupList.propTypes = {
  title: PropTypes.string.isRequired,
  groups: PropTypes.arrayOf(PropTypes.object),
};
GroupList.defaultProps = {
  groups: [],
};

export default GroupList;
