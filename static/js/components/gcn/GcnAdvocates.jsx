import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Chip from "@mui/material/Chip";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import AddGcnAlias from "./AddGcnAlias";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import * as gcnEventsActions from "../../ducks/gcnEvents";

const useStyles = makeStyles(() => ({
  root: {
    margin: "0",
    padding: "0",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  title: {
    margin: 0,
    marginRight: "0.45rem",
    padding: "0",
  },
  addIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
  chips: {
    padding: "0",
    margin: "0",
    "& > div": {
      marginTop: 0,
      marginBottom: 0,
      marginLeft: "0.05rem",
      marginRight: "0.05rem",
    },
  },
  gcnEventDelete: {
    height: "2.1875rem",
    paddingTop: "0.5em",
    paddingBottom: "0.5em",
    alignItems: "center",
  },
}));

const userLabel = (user) => {
  if (!user) {
    return "";
  }
  let label = user.username;
  if (user.first_name && user.last_name) {
    label = `${user.first_name} ${user.last_name} (${user.username})`;
  }
  return label;
};

const GcnAdvocates = ({ gcnEvent, show_title = false }) => {
  const styles = useStyles();

  const dispatch = useDispatch();
  const userProfile = useSelector((state) => state.profile);

  const addUser = async () => {
    const result = await dispatch(
      gcnEventsActions.addGcnEventUser(userProfile.id, gcnEvent.dateobs),
    );
    if (result.status === "success") {
      dispatch(showNotification("GCN Event User successfully added."));
    }
  };

  const deleteUser = async (id) => {
    const result = await dispatch(
      gcnEventsActions.deleteGcnEventUser(id, gcnEvent.dateobs),
    );
    if (result.status === "success") {
      dispatch(showNotification("GCN Event User successfully deleted."));
    }
  };

  return (
    <div className={styles.root}>
      {show_title && <h4 className={styles.title}>Advocates:</h4>}
      <div className={styles.chips} name="gcn_advocates">
        {gcnEvent?.event_users?.map((event_user) => (
          <Tooltip
            key={userLabel(event_user)}
            title={
              <>
                <Button
                  size="small"
                  type="button"
                  name={`deleteGcnEventAdvocateButton${event_user.username}`}
                  onClick={() => deleteUser(event_user.user_id)}
                  className={styles.gcnEventDelete}
                >
                  <DeleteIcon />
                </Button>
              </>
            }
          >
            <Chip
              size="small"
              label={userLabel(event_user)}
              key={userLabel(event_user)}
            />
          </Tooltip>
        ))}
      </div>
      <div>
        <AddIcon
          data-testid="addGcnEventAdvocateIconButton"
          fontSize="small"
          className={styles.addIcon}
          onClick={() => {
            addUser();
          }}
        />
      </div>
    </div>
  );
};

GcnAdvocates.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    event_users: PropTypes.arrayOf(PropTypes.string).isRequired,
  }).isRequired,
  show_title: PropTypes.bool,
};

GcnAdvocates.defaultProps = {
  show_title: false,
};
export default GcnAdvocates;
