import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import DeleteIcon from "@mui/icons-material/Delete";
import { Divider } from "@mui/material";
import makeStyles from "@mui/styles/makeStyles";
import { Link } from "react-router-dom";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import CircularProgress from "@mui/material/CircularProgress";
import PropTypes from "prop-types";
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

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

const userLabel = (user) => {
  let label = user.username;
  if (user.first_name && user.last_name) {
    label = `${user.first_name} ${user.last_name} (${user.username})`;
    if (user.contact_email) {
      label = `${label} (${user.contact_email})`;
    }
    if (user.affiliations && user.affiliations.length > 0) {
      label = `${label} (${user.affiliations.join()})`;
    }
  }
  return label;
};

export function allocationTitle(allocation, instrumentList, telescopeList) {
  const { instrument_id } = allocation;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!(instrument?.name && telescope?.name)) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${instrument?.name}/${telescope?.nickname}`;

  return result;
}

export function allocationInfo(allocation, groups) {
  const group = groups?.filter((g) => g.id === allocation.group_id)[0];

  if (!allocation?.start_date) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const share_groups = [];
  if (allocation.default_share_group_ids?.length > 0) {
    allocation.default_share_group_ids.forEach((share_group_id) => {
      share_groups.push(groups?.filter((g) => g.id === share_group_id)[0].name);
    });
  }

  const allocation_users = [];
  if (allocation.allocation_users?.length > 0) {
    allocation.allocation_users.forEach((user) => {
      allocation_users.push(userLabel(user));
    });
  }

  const startDate = new Date(`${allocation.start_date}Z`).toLocaleString(
    "en-US",
    { hour12: false }
  );
  const endDate = new Date(`${allocation.end_date}Z`).toLocaleString("en-US", {
    hour12: false,
  });
  let result = `From ${startDate} to ${endDate}`;

  if (allocation?.pi || group?.name || share_groups.length > 0) {
    result += "\r\n(";
    if (allocation?.pi) {
      result += `PI: ${allocation.pi}`;
    }
    if (group?.name) {
      result += ` / Group: ${group?.name}`;
    }
    if (share_groups.length > 0) {
      result += ` / Default Share Groups: ${share_groups.join(", ")}`;
    }
    if (allocation_users.length > 0) {
      result += ` / Admins: ${allocation_users.join(", ")}`;
    }
    result += ")";
  }

  return result;
}

const AllocationList = ({ allocations }) => {
  const classes = useStyles();
  const textClasses = textStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  return (
    <div className={classes.root}>
      <List component="nav">
        {allocations?.map((allocation) => (
          <ListItem button key={allocation.id}>
            <ListItemText
              primary={
                <Link
                  to={`/allocation/${allocation.id}`}
                  role="link"
                  className={classes.hover}
                >
                  {allocationTitle(allocation, instrumentList, telescopeList)}
                </Link>
              }
              secondary={allocationInfo(allocation, groups)}
              classes={textClasses}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

AllocationList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  allocations: PropTypes.arrayOf(PropTypes.any).isRequired,
};

const TelescopeInfo = ({ search, searchedTelescopeList }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const currentTelescopes = useSelector(
    (state) => state.telescope.currentTelescopes
  );

  const telescopeList = useSelector((state) => state.telescopes.telescopeList);

  const currentUser = useSelector((state) => state.profile);

  const permission =
    currentUser.permissions?.includes("Delete telescope") ||
    currentUser.permissions?.includes("System admin");

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
  const displaytelescope = (telescope) => (
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
          <div className={classes.telescope_time} key={`${telescope.id}_time`}>
            <i>
              {telescope.morning &&
                `Next Sunrise (Astronomical): ${telescope.morning.slice(
                  0,
                  -4
                )} UTC`}
            </i>
            <i>
              {telescope.evening &&
                `Next Sunset (Astronomical): ${telescope.evening.slice(
                  0,
                  -4
                )} UTC`}
            </i>
          </div>
        )}
        <h3 className={classes.h3} key={`${telescope.id}_diameter`}>
          Diameter : {telescope.diameter ? telescope.diameter.toFixed(1) : null}
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
  );
  // return a list of telescopes with their information
  return (
    <div>
      {search && <List>{searchedTelescopeList.map(displaytelescope)}</List>}
      {currentTelescopes && (
        <List className={classes.root}>
          {currentTelescopes.telescopes.map(displaytelescope)}
        </List>
      )}
      {!currentTelescopes && !search && (
        <List className={classes.root}>
          {telescopeList.map(displaytelescope)}
        </List>
      )}
    </div>
  );
};

TelescopeInfo.propTypes = {
  search: PropTypes.bool,
  // eslint-disable-next-line react/forbid-prop-types
  searchedTelescopeList: PropTypes.arrayOf(PropTypes.any),
};

TelescopeInfo.defaultProps = {
  search: false,
  searchedTelescopeList: [],
};

export default TelescopeInfo;
