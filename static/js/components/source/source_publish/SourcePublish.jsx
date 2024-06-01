import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import CircularProgress from "@mui/material/CircularProgress";
import * as publicSourcePageActions from "../../../ducks/public_pages/public_source_page";
import Button from "../../Button";
import SourcePublishOptions from "./SourcePublishOptions";
import SourcePublishHistory from "./SourcePublishHistory";

const useStyles = makeStyles(() => ({
  expandButton: {
    backgroundColor: "#80808017",
    width: "100%",
    display: "flex",
    justifyContent: "space-between",
    color: "gray",
    fontSize: "1rem",
    borderBottom: "2px solid #e0e0e0",
    borderRadius: "0",
    marginBottom: "0.5rem",
  },
  versionHistoryTitle: {
    marginBottom: "0.5rem",
    fontSize: "1.15rem",
  },
}));

const SourcePublish = ({ sourceId, isPhotometry, isClassifications }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const currentUser = useSelector((state) => state.profile);
  const permissionToPublish =
    currentUser.permissions?.includes("Manage sources");
  const [sourcePublishDialogOpen, setSourcePublishDialogOpen] = useState(false);
  const [publishButton, setPublishButton] = useState({
    text: "Publish",
    color: "",
  });
  const [sourcePublishOptionsOpen, setSourcePublishOptionsOpen] =
    useState(false);
  const [sourcePublishHistoryOpen, setSourcePublishHistoryOpen] =
    useState(true);
  const [versions, setVersions] = useState([]);
  // Create data access options
  const [options, setOptions] = useState({
    include_photometry: true,
    include_classifications: true,
    groups: [],
    streams: [],
  });

  const publish = () => {
    if (permissionToPublish) {
      setPublishButton({ text: "loading", color: "" });
      dispatch(
        publicSourcePageActions.generatePublicSourcePage(sourceId, {
          options,
        }),
      ).then((data) => {
        if (data.status === "error") {
          setPublishButton({ text: "Error", color: "red" });
        } else {
          setPublishButton({ text: "Done", color: "green" });
          if (sourcePublishHistoryOpen) {
            setVersions([data.data, ...versions]);
          }
        }
        setTimeout(() => {
          setPublishButton({ text: "Publish", color: "" });
        }, 2000);
      });
    }
  };

  return (
    <div>
      <Button
        secondary
        size="small"
        onClick={() => setSourcePublishDialogOpen(true)}
      >
        <Tooltip title="Click here if you want to see the public access information">
          <span>Public access</span>
        </Tooltip>
      </Button>
      <Dialog
        open={sourcePublishDialogOpen}
        onClose={() => setSourcePublishDialogOpen(false)}
        PaperProps={{ style: { maxWidth: "700px" } }}
      >
        <DialogTitle>Public access information</DialogTitle>
        <DialogContent style={{ paddingBottom: "0.5rem" }}>
          <div style={{ marginBottom: "1rem" }}>
            You are about to change the public access settings for this source
            page. The data you selected will be available to everyone on the
            internet. Are you sure you want to do this ?
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              margin: "1.5rem 0",
            }}
          >
            <Tooltip
              title={
                permissionToPublish
                  ? ""
                  : "You do not have permission to publish this source"
              }
            >
              <div>
                <Button
                  variant="contained"
                  onClick={publish}
                  style={{
                    backgroundColor: publishButton.color,
                    color: "white",
                  }}
                  disabled={
                    !permissionToPublish || publishButton.text !== "Publish"
                  }
                >
                  {publishButton.text === "loading" ? (
                    <CircularProgress size={24} />
                  ) : (
                    publishButton.text
                  )}
                </Button>
              </div>
            </Tooltip>
          </div>
          {permissionToPublish && (
            <div>
              <Button
                className={styles.expandButton}
                size="small"
                variant="text"
                onClick={() =>
                  setSourcePublishOptionsOpen(!sourcePublishOptionsOpen)
                }
              >
                Options
                {sourcePublishOptionsOpen ? <ExpandLess /> : <ExpandMore />}
              </Button>
              {sourcePublishOptionsOpen && (
                <SourcePublishOptions
                  optionsState={[options, setOptions]}
                  isElements={{
                    photometry: isPhotometry,
                    classifications: isClassifications,
                  }}
                />
              )}
            </div>
          )}
          <div>
            <Button
              className={styles.expandButton}
              size="small"
              variant="text"
              onClick={() =>
                setSourcePublishHistoryOpen(!sourcePublishHistoryOpen)
              }
            >
              Version history
              {sourcePublishHistoryOpen ? <ExpandLess /> : <ExpandMore />}
            </Button>
            {sourcePublishHistoryOpen && (
              <SourcePublishHistory
                sourceId={sourceId}
                versions={versions}
                setVersions={setVersions}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

SourcePublish.propTypes = {
  sourceId: PropTypes.string.isRequired,
  isPhotometry: PropTypes.bool.isRequired,
  isClassifications: PropTypes.bool.isRequired,
};

export default SourcePublish;
