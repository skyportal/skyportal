import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Chip from "@mui/material/Chip";
import DeleteIcon from "@mui/icons-material/Delete";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import AddGcnAlias from "../AddGcnAlias";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import * as gcnEventActions from "../../ducks/gcnEvent";

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
  aliasDelete: {
    height: "2.1875rem",
    paddingTop: "0.5em",
    paddingBottom: "0.5em",
    alignItems: "center",
  },
}));

const GcnAliases = ({ gcnEvent, show_title = false }) => {
  const styles = useStyles();

  const dispatch = useDispatch();

  const userProfile = useSelector((state) => state.profile);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [aliasToDelete, setAliasToDelete] = useState(null);
  const openDialog = (tag) => {
    setDialogOpen(true);
    setAliasToDelete(tag);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setAliasToDelete(null);
  };

  const deleteAlias = () => {
    dispatch(
      gcnEventActions.deleteGcnAlias(gcnEvent.dateobs, {
        alias: aliasToDelete,
      }),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("GCN Event Alias deleted"));
        closeDialog();
      }
    });
  };

  const permission =
    userProfile.permissions.includes("System admin") ||
    userProfile.permissions.includes("Manage GCNs");

  return (
    <div className={styles.root}>
      {show_title && <h4 className={styles.title}>Aliases:</h4>}
      <div className={styles.chips} name="gcn_triggers-aliases">
        {gcnEvent?.aliases?.map((alias) => (
          <Tooltip
            key={alias}
            title={
              <>
                <Button
                  size="small"
                  type="button"
                  name={`deleteAliasButton${alias}`}
                  onClick={() => openDialog(alias)}
                  disabled={!permission}
                  className={styles.aliasDelete}
                >
                  <DeleteIcon />
                </Button>
                <ConfirmDeletionDialog
                  deleteFunction={deleteAlias}
                  dialogOpen={dialogOpen}
                  closeDialog={closeDialog}
                  resourceName="alias"
                />
              </>
            }
          >
            <Chip
              size="small"
              label={alias}
              key={alias}
              clickable
              onClick={() => {
                window.open(
                  `https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/?event=${
                    alias.split("#")[1] || alias
                  }`,
                  "_blank",
                );
              }}
            />
          </Tooltip>
        ))}
      </div>
      <div>
        <AddGcnAlias gcnEvent={gcnEvent} />
      </div>
    </div>
  );
};

GcnAliases.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    aliases: PropTypes.arrayOf(PropTypes.string).isRequired,
  }).isRequired,
  show_title: PropTypes.bool,
};

GcnAliases.defaultProps = {
  show_title: false,
};
export default GcnAliases;
