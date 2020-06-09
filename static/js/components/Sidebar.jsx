import React from "react";
import { Link } from "react-router-dom";
import { makeStyles } from "@material-ui/core/styles";
import Drawer from "@material-ui/core/Drawer";
import List from "@material-ui/core/List";
import Divider from "@material-ui/core/Divider";
import ListItem from "@material-ui/core/ListItem";
import ListItemIcon from "@material-ui/core/ListItemIcon";
import ListItemText from "@material-ui/core/ListItemText";
import { blue } from "@material-ui/core/colors";
import HomeIcon from "@material-ui/icons/Home";
import SearchIcon from "@material-ui/icons/Search";
import AccountBoxIcon from "@material-ui/icons/AccountBox";


const drawerWidth = 190;

const useStyles = makeStyles(() => ({
  drawer: {
    width: drawerWidth,
    flexShrink: 0,
  },
  drawerPaper: {
    width: drawerWidth,
    paddingLeft: "0.4em",
    background: "#33345C",
    color: "#B8D2FF",
    fontSize: "1.2em",
    paddingTop: "6em"
  },
  toolbar: {
    display: "flex",
    height: "4em",
    padding: "1em 0em",
    alignItems: "center",
  },
  description: {
    margin: "0em",
    padding: "0em",
    fontSize: "0.6em",
    color: "#ccc"
  },
  icon: {
    width: "1.6em",
    height: "1.6em"
  },
  link: {
    color: "#B8D2FF",
    textDecoration: "none"
  }
}));


const MyDrawer = () => {
  const classes = useStyles();
  const iconMap = {
    // Dashboard: <img className={classes.icon} src="/static/images/home.png" alt="" />,
    // Dashboard: <img className={classes.icon}
    // src="/static/images/figma_icon/iconfinder_house_384890.svg" alt="" />,
    // Source: <img className={classes.icon} src="/static/images/search.png" alt="" />,
    // Source: <img className={classes.icon}
    // src="/static/images/figma_icon/iconfinder_search_322497.svg" alt="" />,
    // Profile: <img className={classes.icon} src="/static/images/profile.png" alt="" />
    Dashboard: <HomeIcon style={{ color: blue[200] }} />,
    Candidates: <SearchIcon style={{ color: blue[200] }} />,
    Profile: <AccountBoxIcon style={{ color: blue[200] }} />

  };

  return (
    <Drawer
      className={classes.drawer}
      variant="permanent"
      classes={{
        paper: classes.drawerPaper,
      }}
      anchor="left"
    >
      <List>
        <Link to="/" className={classes.link}>
          <ListItem button name="sidebarDashboardButton">
            <ListItemIcon>
              {' '}
              {iconMap.Dashboard}
              {' '}
            </ListItemIcon>
            <ListItemText primary="Dashboard" />
          </ListItem>
        </Link>
        <Link to="/candidates" className={classes.link}>
          <ListItem button name="sidebarCandidatesButton">
            <ListItemIcon>
              {' '}
              {iconMap.Candidates}
              {' '}
            </ListItemIcon>
            <ListItemText primary="Candidates" />
          </ListItem>
        </Link>
        <Link to="/profile" className={classes.link}>
          <ListItem button name="sidebarProfileButton">
            <ListItemIcon>
              {' '}
              {iconMap.Profile}
              {' '}
            </ListItemIcon>
            <ListItemText primary="Profile" />
          </ListItem>
        </Link>
      </List>
      <Divider />
    </Drawer>
  );
};

export default MyDrawer;
