import React, { useState, useEffect } from "react";
import makeStyles from "@mui/styles/makeStyles";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import CircularProgress from "@mui/material/CircularProgress";
import * as publicSourcePageActions from "../../../ducks/public_pages/public_source_page";
import Button from "../../Button";
import {
  getThumbnailAltAndLink,
  getThumbnailHeader,
} from "../../thumbnail/Thumbnail";
import SourcePublishOptions from "./SourcePublishOptions";
import SourcePublishHistory from "./SourcePublishHistory";

const useStyles = makeStyles(() => ({
  expandButton: {
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

const SourcePublish = ({ source, photometry = null }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const currentUser = useSelector((state) => state.profile);
  const permissionToPublish = currentUser.permissions?.includes(
    "Manage sources publishing",
  );
  const [sourcePublishDialogOpen, setSourcePublishDialogOpen] = useState(false);
  const [publishButton, setPublishButton] = useState("publish");
  const [sourcePublishOptionsOpen, setSourcePublishOptionsOpen] =
    useState(false);
  const [sourcePublishHistoryOpen, setSourcePublishHistoryOpen] =
    useState(false);
  const [newPageGenerate, setNewPageGenerate] = useState(null);
  const [updateThumbnailsData, setUpdateThumbnailsData] = useState(false);
  // Create data access options
  const optionPhotometry = { label: "photometry", state: useState(true) };
  const optionClassifications = {
    label: "classifications",
    state: useState(true),
  };

  const getOptions = () => [
    {
      label: optionPhotometry.label,
      isElement: source.photometry_exists,
      isCheck: optionPhotometry.state[0],
      setCheck: optionPhotometry.state[1],
    },
    {
      label: optionClassifications.label,
      isElement: source.classifications.length > 0,
      isCheck: optionClassifications.state[0],
      setCheck: optionClassifications.state[1],
    },
  ];

  useEffect(() => {
    setUpdateThumbnailsData(true);
  }, [source.thumbnails]);

  // Add alt, link and header to thumbnails
  const processThumbnailsData = () => {
    source.thumbnails.forEach((thumbnail) => {
      const { alt, link } = getThumbnailAltAndLink(
        thumbnail.type,
        source.ra,
        source.dec,
      );
      thumbnail.alt = alt;
      thumbnail.link = link;
      thumbnail.header = getThumbnailHeader(thumbnail.type);
    });
    setUpdateThumbnailsData(false);
  };

  const publicData = () => {
    if (!source) return null;
    if (updateThumbnailsData) {
      processThumbnailsData();
    }
    const getPhotometry = () => {
      if (!source.photometry_exists) {
        return [];
      }
      return photometry;
    };
    return {
      source_id: source.id,
      radec_hhmmss: source.radec_hhmmss,
      ra: source.ra,
      dec: source.dec,
      gal_lon: source.gal_lon?.toFixed(6),
      gal_lat: source.gal_lat?.toFixed(6),
      ebv: source.ebv?.toFixed(2),
      redshift: source.redshift?.toFixed(source.z_round),
      dm: source.dm?.toFixed(3),
      dl: source.luminosity_distance?.toFixed(2),
      thumbnails: source.thumbnails,
      photometry: optionPhotometry.state[0] ? getPhotometry() : null,
      classifications: optionClassifications.state[0]
        ? source.classifications
        : null,
    };
  };

  const publish = () => {
    if (!permissionToPublish) return;
    setPublishButton("loading");
    const payload = {
      public_data: publicData(),
    };
    dispatch(
      publicSourcePageActions.generatePublicSourcePage(source.id, payload),
    ).then((data) => {
      setPublishButton("done");
      setNewPageGenerate(data.data.page);
      setTimeout(() => {
        setPublishButton("publish");
      }, 2000);
    });
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
            page. This information will be available to everyone on the
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
                    backgroundColor: publishButton === "done" ? "green" : "",
                    color: "white",
                  }}
                  disabled={!permissionToPublish || publishButton !== "publish"}
                >
                  {publishButton === "loading" ? (
                    <CircularProgress size={24} />
                  ) : (
                    publishButton
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
                <SourcePublishOptions options={getOptions()} />
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
                source_id={source.id}
                newPageGenerate={newPageGenerate}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

SourcePublish.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    ra: PropTypes.number,
    dec: PropTypes.number,
    radec_hhmmss: PropTypes.string,
    gal_lat: PropTypes.number,
    gal_lon: PropTypes.number,
    ebv: PropTypes.number,
    redshift: PropTypes.number,
    z_round: PropTypes.number,
    dm: PropTypes.number,
    luminosity_distance: PropTypes.number,
    thumbnails: PropTypes.arrayOf(PropTypes.shape({})),
    photometry_exists: PropTypes.bool,
    classifications: PropTypes.arrayOf(PropTypes.shape({})),
    is_public: PropTypes.bool,
  }).isRequired,
  photometry: PropTypes.arrayOf(PropTypes.shape({})),
};

SourcePublish.defaultProps = {
  photometry: null,
};

export default SourcePublish;
