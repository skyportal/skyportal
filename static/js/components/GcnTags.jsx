import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import Chip from "@mui/material/Chip";
import DeleteIcon from "@mui/icons-material/Delete";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import AddGcnTag from "./AddGcnTag";
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";

import * as gcnTagsActions from "../ducks/gcnTags";

const useStyles = makeStyles(() => ({
  root: {
    margin: "0",
    padding: "0",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  BNS: {
    background: "#468847!important",
  },
  NSBH: {
    background: "#b94a48!important",
  },
  BBH: {
    background: "#333333!important",
  },
  GRB: {
    background: "#f89406!important",
  },
  AMON: {
    background: "#3a87ad!important",
  },
  Terrestrial: {
    background: "#999999!important",
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
  tagDelete: {
    height: "2.1875rem",
    paddingTop: "0.5em",
    paddingBottom: "0.5em",
    alignItems: "center",
  },
}));

const GcnTags = ({ gcnEvent, show_title = false }) => {
  const styles = useStyles();

  const dispatch = useDispatch();

  const userProfile = useSelector((state) => state.profile);

  const gcn_tags_classes = useSelector((state) => state.config.gcnTagsClasses);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [tagToDelete, setTagToDelete] = useState(null);
  const openDialog = (tag) => {
    setDialogOpen(true);
    setTagToDelete(tag);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setTagToDelete(null);
  };

  const deleteTag = () => {
    dispatch(gcnTagsActions.deleteGcnTag(gcnEvent.dateobs, tagToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("GCN Event Tag deleted"));
          closeDialog();
        }
      }
    );
  };

  const gcnTags = [];
  gcnEvent.tags?.forEach((tag) => {
    gcnTags.push(tag);
  });
  const gcnTagsUnique = [...new Set(gcnTags)];

  const localizationTags = [];
  gcnEvent.localizations?.forEach((loc) => {
    loc.tags?.forEach((tag) => {
      localizationTags.push(tag.text);
    });
  });
  const localizationTagsUnique = [...new Set(localizationTags)];

  const permission =
    userProfile.permissions.includes("System admin") ||
    userProfile.permissions.includes("Manage GCNs");

  return (
    <div className={styles.root}>
      {show_title && <h4 className={styles.title}>Tags:</h4>}
      <div className={styles.chips} name="gcn_triggers-tags">
        {gcnTagsUnique.map((tag) => (
          <Tooltip
            key={tag}
            title={
              <>
                <Button
                  size="small"
                  type="button"
                  name={`deleteTagButton${tag}`}
                  onClick={() => openDialog(tag)}
                  disabled={!permission}
                  className={styles.tagDelete}
                >
                  <DeleteIcon />
                </Button>
                <ConfirmDeletionDialog
                  deleteFunction={deleteTag}
                  dialogOpen={dialogOpen}
                  closeDialog={closeDialog}
                  resourceName="tag"
                />
              </>
            }
          >
            <Chip className={styles[tag]} size="small" label={tag} key={tag} />
          </Tooltip>
        ))}
        {localizationTagsUnique.map((tag) => (
          <Chip
            size="small"
            label={tag}
            key={tag}
            style={{ backgroundColor: gcn_tags_classes[tag] }}
          />
        ))}
      </div>
      <div>
        <AddGcnTag gcnEvent={gcnEvent} />
      </div>
    </div>
  );
};

GcnTags.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    tags: PropTypes.arrayOf(PropTypes.string).isRequired,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      })
    ),
  }).isRequired,
  show_title: PropTypes.bool,
};

GcnTags.defaultProps = {
  show_title: false,
};
export default GcnTags;
