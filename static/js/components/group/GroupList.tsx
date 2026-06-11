import { Link } from "react-router-dom";
import Paper from "@mui/material/Paper";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import { makeStyles } from "tss-react/mui";

import { Group } from "../../types";

const useStyles = makeStyles()(() => ({
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

interface GroupListProps {
  title: string;
  groups?: Group[];
  classes: {
    widgetPaperDiv: string;
    widgetIcon: string;
    widgetPaperFillSpace: string;
  };
  linkToGroupSources?: boolean;
}

const GroupList = ({
  title,
  groups = [],
  classes,
  linkToGroupSources = false,
}: GroupListProps) => {
  const { classes: styles } = useStyles();

  const getLink = (group: Group) =>
    linkToGroupSources ? `/group_sources/${group.id}` : `/group/${group.id}`;

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
                <Link to={getLink(group)} key={group.id}>
                  <ListItemButton data-testid={`${title}-${group.name}`}>
                    <ListItemText primary={group.name} />
                  </ListItemButton>
                </Link>
              ))}
        </List>
      </div>
    </Paper>
  );
};

export default GroupList;
