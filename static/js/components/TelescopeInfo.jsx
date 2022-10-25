import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import DeleteIcon from "@mui/icons-material/Delete";
import { Divider } from "@mui/material";
import makeStyles from "@mui/styles/makeStyles";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";

import * as telescopeActions from "../ducks/telescope";

const useStyles = makeStyles(() => ({
  root: {
    width: "100%",
    height: "100%",
    padding: "1rem",
    gap: "1rem",
    maxHeight: "85vh",
    overflowY: "auto",
  },
  listItem: {
    display: "flex",
    flexDirection: "column",
    justifyItems: "left",
    alignItems: "left",
  },
  telescope_header: {
    display: "flex",
    flexDirection: "row",
    justifyItems: "center",
    alignItems: "center",
    gap: "0.5rem",
  },
  h2: {
    textAlign: "left",
    fontSize: "1.4rem",
    padding: "0",
    margin: "0",
  },
  h3: {
    textAlign: "left",
    fontSize: "1rem",
    marginTop: "0.5rem",
    padding: "0",
    margin: "0",
  },
  a: {
    textAlign: "left",
    fontSize: "0.8rem",
    marginTop: "1rem",
    padding: "0",
    margin: "0",
  },
  canObserveFixed: {
    height: "1rem",
    width: "1rem",
    backgroundColor: "#0c1445",
    borderRadius: "50%",
  },
  cannotObserveFixed: {
    height: "1rem",
    width: "1rem",
    backgroundColor: "#f9d71c",
    borderRadius: "50%",
  },
  cannotObserveNonFixed: {
    height: "1rem",
    width: "1rem",
    backgroundColor: "#5ca9d6",
  },
  telescope_time: {
    display: "flex",
    flexDirection: "column",
    justifyItems: "left",
    alignItems: "left",
  },
  telescopeDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  telescopeDeleteDisabled: {
    opacity: 0,
  },
}));

const TelescopeInfo = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const currentTelescopes = useSelector(
    (state) => state.telescope.currentTelescopes
  );

  const currentUser = useSelector((state) => state.profile);

  const permission = currentUser.permissions?.includes("System admin");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [telescopeToDelete, setTelescopeToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setTelescopeToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setTelescopeToDelete(null);
  };

  const deleteTelescope = () => {
    dispatch(telescopeActions.deleteTelescope(telescopeToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Telescope deleted"));
          closeDialog();
        }
      }
    );
  };

  // return a list of telescopes with their information
  return currentTelescopes ? (
    <List className={classes.root}>
      {currentTelescopes.telescopes.map((telescope) => (
        <div key={`${telescope.id}_list_item`}>
          <ListItem
            id={`${telescope.name}_info`}
            className={classes.listItem}
            key={`${telescope.id}_info`}
          >
            <div
              className={classes.telescope_header}
              key={`${telescope.id}_header`}
            >
              {telescope.is_night_astronomical && telescope.fixed_location && (
                <span className={classes.canObserveFixed} />
              )}
              {!telescope.is_night_astronomical && telescope.fixed_location && (
                <span className={classes.cannotObserveFixed} />
              )}
              {!telescope.fixed_location && (
                <span className={classes.cannotObserveNonFixed} />
              )}
              <h2 className={classes.h2}>
                {telescope.name} ({telescope.nickname})
              </h2>
            </div>
            {telescope.fixed_location && (
              <div
                className={classes.telescope_time}
                key={`${telescope.id}_time`}
              >
                <i>
                  {telescope.next_twilight_morning_astronomical &&
                    `Next Sunrise (Astronomical): ${telescope.next_twilight_morning_astronomical.slice(
                      0,
                      -4
                    )} UTC`}
                </i>
                <i>
                  {telescope.next_twilight_evening_astronomical &&
                    `Next Sunset (Astronomical): ${telescope.next_twilight_evening_astronomical.slice(
                      0,
                      -4
                    )} UTC`}
                </i>
              </div>
            )}
            <h3 className={classes.h3} key={`${telescope.id}_diameter`}>
              Diameter :{" "}
              {telescope.diameter ? telescope.diameter.toFixed(1) : null}
            </h3>
            {telescope.fixed_location && (
              <h3 className={classes.h3} key={`${telescope.id}_location`}>
                Location : {telescope.lat ? telescope.lat.toFixed(4) : null},{" "}
                {telescope.lon ? telescope.lon.toFixed(4) : null}
              </h3>
            )}
            {telescope.fixed_location && (
              <h3 className={classes.h3} key={`${telescope.id}_elevation`}>
                Elevation :{" "}
                {telescope.elevation ? telescope.elevation.toFixed(1) : null}
              </h3>
            )}
            {telescope.robotic ? (
              <h3 className={classes.h3} key={`${telescope.id}_robotic`}>
                Robotic : Yes
              </h3>
            ) : (
              <h3 className={classes.h3} key={`${telescope.id}_robotic`}>
                Robotic : No
              </h3>
            )}
            {telescope.fixed_location ? (
              <h3 className={classes.h3} key={`${telescope.id}_fixed_location`}>
                Fixed Location : Yes
              </h3>
            ) : (
              <h3 className={classes.h3} key={`${telescope.id}_fixed_location`}>
                Fixed Location : No
              </h3>
            )}
            {telescope.skycam_link && (
              <a
                className={classes.a}
                href={telescope.skycam_link}
                key={`${telescope.id}_skycam_link`}
              >
                skycam link
              </a>
            )}
            <Button
              key={telescope.id}
              id="delete_button"
              classes={{
                root: classes.telescopeDelete,
                disabled: classes.telescopeDeleteDisabled,
              }}
              onClick={() => openDialog(telescope.id)}
              disabled={!permission}
            >
              <DeleteIcon />
            </Button>
            <ConfirmDeletionDialog
              deleteFunction={deleteTelescope}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="telescope"
            />
          </ListItem>
          <Divider />
        </div>
      ))}
    </List>
  ) : (
    <h2 className={classes.h2}>No telescope selected</h2>
  );
};

export default TelescopeInfo;
