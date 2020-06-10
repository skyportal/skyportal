import React from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import { Link } from "react-router-dom";
import clsx from "clsx";
import Drawer from "@material-ui/core/Drawer";
import AppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar';
import List from "@material-ui/core/List";
import Divider from "@material-ui/core/Divider";
import ListItem from "@material-ui/core/ListItem";
import ListItemIcon from "@material-ui/core/ListItemIcon";
import ListItemText from "@material-ui/core/ListItemText";
import { blue } from "@material-ui/core/colors";
import HomeIcon from "@material-ui/icons/Home";
import SearchIcon from "@material-ui/icons/Search";
import AccountBoxIcon from "@material-ui/icons/AccountBox";
import InfoIcon from "@material-ui/icons/Info";
import MenuIcon from "@material-ui/icons/Menu";
import IconButton from "@material-ui/core/IconButton";
import ChevronLeftIcon from '@material-ui/icons/ChevronLeft';

import useStyles from "./muiStyles";
import HeaderContent from "./HeaderContent";
import * as Actions from "../ducks/sidebar";


const SidebarAndHeader = ({ open, root }) => {
  const dispatch = useDispatch();
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
    Profile: <AccountBoxIcon style={{ color: blue[200] }} />,
    About: <InfoIcon style={{ color: blue[200] }} />,

  };

  const handleToggleSidebarOpen = () => {
    dispatch(Actions.toggleSidebar());
  };

  return (
    <>
      <AppBar
        position="fixed"
        className={clsx(classes.appBar, {
          [classes.appBarShift]: open,
        })}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            onClick={handleToggleSidebarOpen}
            edge="start"
            className={clsx(classes.menuButton, open && classes.hide)}
          >
            <MenuIcon />
          </IconButton>
          <HeaderContent root={root} />
        </Toolbar>
      </AppBar>
      <Drawer
        className={classes.drawer}
        variant="persistent"
        anchor="left"
        open={open}
        classes={{
          paper: classes.drawerPaper,
        }}
      >
        <div className={classes.drawerHeader}>
          <IconButton onClick={handleToggleSidebarOpen}>
            <ChevronLeftIcon />
          </IconButton>
        </div>
        <Divider />
        <List>
          <Link to="/" className={classes.link}>
            <ListItem button name="sidebarDashboardButton">
              <ListItemIcon>
                {" "}
                {iconMap.Dashboard}
                {" "}
              </ListItemIcon>
              <ListItemText primary="Dashboard" />
            </ListItem>
          </Link>
          <Link to="/candidates" className={classes.link}>
            <ListItem button name="sidebarCandidatesButton">
              <ListItemIcon>
                {" "}
                {iconMap.Candidates}
                {" "}
              </ListItemIcon>
              <ListItemText primary="Candidates" />
            </ListItem>
          </Link>
          <Link to="/profile" className={classes.link}>
            <ListItem button name="sidebarProfileButton">
              <ListItemIcon>
                {" "}
                {iconMap.Profile}
                {" "}
              </ListItemIcon>
              <ListItemText primary="Profile" />
            </ListItem>
          </Link>
          <Link to="/about" className={classes.link}>
            <ListItem button name="sidebarAboutButton">
              <ListItemIcon>
                {" "}
                {iconMap.About}
                {" "}
              </ListItemIcon>
              <ListItemText primary="About" />
            </ListItem>
          </Link>
        </List>
      </Drawer>
    </>
  );
};

SidebarAndHeader.propTypes = {
  open: PropTypes.bool.isRequired,
  root: PropTypes.string.isRequired
};

export default SidebarAndHeader;
