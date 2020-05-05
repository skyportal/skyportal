import React from 'react';
import { makeStyles } from '@material-ui/core/styles';
import Drawer from '@material-ui/core/Drawer';
import List from '@material-ui/core/List';
import Divider from '@material-ui/core/Divider';
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemText from '@material-ui/core/ListItemText';

import { blue } from '@material-ui/core/colors';

import FaceIcon from '@material-ui/icons/Face';
import HomeIcon from '@material-ui/icons/Home';
import SearchIcon from '@material-ui/icons/Search';
import AccountBoxIcon from '@material-ui/icons/AccountBox';


const drawerWidth = 190;

const useStyles = makeStyles(theme => ({
  drawer: {
    width: drawerWidth,
    flexShrink: 0,
  },
  drawerPaper: {
    width: drawerWidth,
    paddingLeft: "0.4em",
    background: "#00045C",
    color: "#B8D2FF",
    fontSize: "1.2em"
  },
  toolbar: {
    display: "flex",
    height: "4em",
    padding: "1em 0em",
    alignItems: "center",
  },
  profileNameBox: {
    display: "block",
    padding: "0em 0.3em"
  },
  description: {
    margin: "0em",
    padding: "0em",
    fontSize: "0.6em",
    color: "#ccc"
  },
  // theme.mixins.toolbar,
  icon: {
    width: "1.6em",
    height: "1.6em"
  }
}));


const drawer = () => {
    const classes = useStyles();
    const iconMap = {
        // Dashboard: <img className={classes.icon} src="/static/images/home.png" alt="" />,
        // Dashboard: <img className={classes.icon} src="/static/images/figma_icon/iconfinder_house_384890.svg" alt="" />,
        // Source: <img className={classes.icon} src="/static/images/search.png" alt="" />,
        // Source: <img className={classes.icon} src="/static/images/figma_icon/iconfinder_search_322497.svg" alt="" />,
        // Profile: <img className={classes.icon} src="/static/images/profile.png" alt="" />
        Dashboard: <HomeIcon style={{ color: blue[200] }} />,
        Source: <SearchIcon style={{ color: blue[200] }} />,
        Profile: <AccountBoxIcon style={{ color: blue[200] }} />

    }

    return (
      <Drawer
          className={classes.drawer}
          variant="permanent"
          classes={{
          paper: classes.drawerPaper,
          }}
          anchor="left"
      >
          <div className={classes.toolbar}> 
            <FaceIcon style={{ fontSize: "4.2em" }}/> 
            <div className={classes.profileNameBox}>
              Alex Wu
              <p className={classes.description}> Front End Dev </p>
            </div>
          </div>
          <Divider />
          <List>
          {['Dashboard', 'Source', 'Profile'].map((text, index) => (
              <ListItem button key={text}>
                <ListItemIcon> {iconMap[text]} </ListItemIcon>
                <ListItemText primary={text} />
              </ListItem>
          ))}
          </List>
          <Divider />
      </Drawer>
)};

export default drawer;