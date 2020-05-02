import React from 'react';
import { makeStyles } from '@material-ui/core/styles';
import Drawer from '@material-ui/core/Drawer';
import List from '@material-ui/core/List';
import Divider from '@material-ui/core/Divider';
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemText from '@material-ui/core/ListItemText';


const drawerWidth = 180;

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
  toolbar: theme.mixins.toolbar,
  icon: {
    width: "1.6em",
    height: "1.6em"
  }
}));


const drawer = () => {
    const classes = useStyles();
    const iconMap = {
        Dashboard: <img className={classes.icon} src="/static/images/home.png" alt="" />,
        Source: <img className={classes.icon} src="/static/images/search.png" alt="" />,
        Profile: <img className={classes.icon} src="/static/images/profile.png" alt="" />
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
            <div className={classes.toolbar} />
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