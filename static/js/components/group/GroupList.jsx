import React from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import DragHandleIcon from "@mui/icons-material/DragHandle";

import Paper from "../Paper";

const GroupList = ({ title, groups, classes, listMaxHeight }) => {
  if (!groups?.length) return null;
  const multiUserGroups = groups.filter((group) => !group.single_user_group);

  return (
    <Paper sx={{ height: "100%", overflowY: "hidden" }}>
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Typography variant="h6">{title}</Typography>
        <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
      </Box>
      <Box sx={{ overflowY: "scroll", maxHeight: listMaxHeight || "none" }}>
        <List>
          {multiUserGroups.map((group) => (
            <Link to={`/group/${group.id}`} key={group.id}>
              <ListItem data-testid={`${title}-${group.name}`}>
                <ListItemText primary={group.name} />
              </ListItem>
            </Link>
          ))}
        </List>
      </Box>
    </Paper>
  );
};

GroupList.propTypes = {
  title: PropTypes.string.isRequired,
  groups: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      single_user_group: PropTypes.bool,
    }),
  ),
  classes: PropTypes.shape({
    widgetIcon: PropTypes.string.isRequired,
  }).isRequired,
  listMaxHeight: PropTypes.string,
};

export default GroupList;
