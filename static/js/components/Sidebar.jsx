import React from 'react';
import { makeStyles } from '@material-ui/core/styles';
import Drawer from '@material-ui/core/Drawer';
import List from '@material-ui/core/List';
import Divider from '@material-ui/core/Divider';
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemText from '@material-ui/core/ListItemText';

import DashboardIcon from '@material-ui/icons/Dashboard';
import FlareIcon from '@material-ui/icons/Flare';
import AccountBoxIcon from '@material-ui/icons/AccountBox';

const drawerWidth = 170;

const useStyles = makeStyles(theme => ({
  drawer: {
    width: drawerWidth,
    flexShrink: 0,
  },
  drawerPaper: {
    width: drawerWidth,
  },
  toolbar: theme.mixins.toolbar,
}));


const drawer = () => {
    const classes = useStyles();
    const iconMap = {
        Dashboard: <DashboardIcon/>,
        Source: <FlareIcon/>,
        Profile: <AccountBoxIcon />
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