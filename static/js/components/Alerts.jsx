import React, { useState } from "react";

import Badge from "@mui/material/Badge";
import ErrorIcon from "@mui/icons-material/ErrorOutline";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import makeStyles from "@mui/styles/makeStyles";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Divider from "@mui/material/Divider";
import ReactMarkdown from "react-markdown";
import Button from "./Button";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: 360,
    backgroundColor: theme.palette.background.paper,
  },
  centered: {
    display: "flex",
    justifyContent: "center",
  },
}));

const Alerts = () => {
  const classes = useStyles();
  const alerts = [];
  const [anchorEl, setAnchorEl] = useState(null);

  const handleClickOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const deleteAllAlerts = () => {
    handleClose();
  };

  const deleteAlert = () => {};

  return (
    <>
      <IconButton
        onClick={handleClickOpen}
        data-testid="alertsButton"
        size="large"
        style={{ padding: 0, margin: 0 }}
      >
        <Badge
          badgeContent={alerts.length}
          overlap="circular"
          color={alerts.length > 0 ? "secondary" : "primary"}
          data-testid="alertsBadge"
        >
          <ErrorIcon fontSize="large" color="primary" />
        </Badge>
      </IconButton>
      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "center",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "center",
        }}
        disableScrollLock
      >
        <div className={classes.root}>
          <List className={classes.root}>
            {alerts &&
              alerts.map((alert) => (
                <div key={alert.id}>
                  <ListItem data-testid={`alert_${alert.id}`}>
                    <ReactMarkdown>{alert.text}</ReactMarkdown>
                  </ListItem>
                  <ListItem className={classes.centered}>
                    <Button
                      data-testid={`deleteAlertButton${alert.id}`}
                      size="small"
                      onClick={() => {
                        deleteAlert(alert.id);
                      }}
                    >
                      Delete
                    </Button>
                  </ListItem>
                  <Divider />
                </div>
              ))}
            {alerts && alerts.length > 0 && (
              <Button
                onClick={deleteAllAlerts}
                data-testid="deleteAllAlertsButton"
              >
                Delete all
              </Button>
            )}
            {(!alerts || alerts.length === 0) && (
              <ListItem className={classes.centered}>
                <em>No alerts</em>
              </ListItem>
            )}
          </List>
        </div>
      </Popover>
    </>
  );
};

export default Alerts;
