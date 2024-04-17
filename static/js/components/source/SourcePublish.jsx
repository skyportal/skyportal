import React, { useEffect, useState } from "react";
import makeStyles from "@mui/styles/makeStyles";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import {
  getThumbnailAltAndLink,
  getThumbnailHeader,
} from "../thumbnail/Thumbnail";
import Button from "../Button";
import * as accessibilityActions from "../../ducks/source_accessibility";

const useStyles = makeStyles(() => ({
  buttons: {
    display: "flex",
    justifyContent: "space-around",
  },
  dataToPublishForm: {
    display: "flex",
    flexDirection: "column",
    marginBottom: "2rem",
    paddingLeft: "2rem",
  },
  linkToPublic: {
    display: "flex",
    alignItems: "center",
    margin: "0.25rem 0",
  },
}));

const SourcePublish = ({ classes, source, photometry = null }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const [isPublished, setIsPublished] = useState(source.is_public);
  const [publishedDialogOpen, setPublishedDialogOpen] = useState(false);
  const [includePhotometry, setIncludePhotometry] = useState(true);
  const [includeClassifications, setIncludeClassifications] = useState(true);
  const [updateThumbnailsData, setUpdateThumbnailsData] = useState(false);

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
      photometry:
        includePhotometry && source.photometry_exists && photometry?.length
          ? photometry
          : null,
      classifications: includeClassifications ? source.classifications : null,
    };
  };

  const publish = () => {
    const payload = {
      publish: true,
      public_data: publicData(),
    };
    dispatch(
      accessibilityActions.updateSourceAccessibility(source.id, payload),
    ).then(() => {
      setIsPublished(true);
    });
    setPublishedDialogOpen(false);
  };

  const unpublish = () => {
    const payload = { publish: false };
    dispatch(
      accessibilityActions.updateSourceAccessibility(source.id, payload),
    ).then(() => {
      setIsPublished(false);
    });
  };

  return (
    <div className={classes.infoButton}>
      <Button
        secondary
        size="small"
        data-testid="publishButton"
        onClick={() =>
          isPublished ? unpublish() : setPublishedDialogOpen(true)
        }
      >
        <Tooltip
          title={
            isPublished
              ? "Click here if you want to make this source private"
              : "Click here if you want to make this source public"
          }
        >
          <span>{isPublished ? "Unpublish" : "Publish"}</span>
        </Tooltip>
      </Button>
      <Dialog
        open={publishedDialogOpen}
        onClose={() => setPublishedDialogOpen(false)}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Publish this source</DialogTitle>
        <DialogContent>
          <div style={{ marginBottom: "1rem" }}>
            You are about to publish this source page. This information will be
            available to everyone on the Internet. Are you sure you want to do
            this ?
          </div>
          <div className={styles.buttons}>
            <Button
              secondary
              size="small"
              data-testid="areYouSurPublishButton"
              onClick={() => {
                publish();
              }}
            >
              Yes
            </Button>
            <Button
              secondary
              size="small"
              data-testid="areYouSurCancelPublishButton"
              onClick={() => {
                setPublishedDialogOpen(false);
              }}
            >
              Cancel
            </Button>
          </div>
          <div className={styles.dataToPublishForm}>
            <FormControlLabel
              label="Include photometry?"
              control={
                <Checkbox
                  color="primary"
                  title="Include photometry?"
                  type="checkbox"
                  onChange={(event) =>
                    setIncludePhotometry(event.target.checked)
                  }
                  checked={includePhotometry}
                />
              }
            />
            <FormControlLabel
              label="Include classifications?"
              control={
                <Checkbox
                  color="primary"
                  title="Include classifications?"
                  type="checkbox"
                  onChange={(event) =>
                    setIncludeClassifications(event.target.checked)
                  }
                  checked={includeClassifications}
                />
              }
            />
          </div>
          <div
            className="style.linkToPublic"
            style={{
              display: "flex",
              alignItems: "center",
              margin: "0.25rem 0",
            }}
          >
            <a
              href={`/public/sources/${source.id}`}
              target="_blank"
              rel="noreferrer"
            >
              See public page
            </a>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

SourcePublish.propTypes = {
  classes: PropTypes.shape({
    infoButton: PropTypes.string,
  }).isRequired,
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
    photometry: PropTypes.arrayOf(PropTypes.shape({})),
    classifications: PropTypes.arrayOf(PropTypes.shape({})),
    is_public: PropTypes.bool,
  }).isRequired,
  photometry: PropTypes.arrayOf(PropTypes.shape({})),
};

SourcePublish.defaultProps = {
  photometry: null,
};

export default SourcePublish;
