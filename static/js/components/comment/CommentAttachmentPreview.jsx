import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import { useTheme } from "@mui/material/styles";
import withStyles from "@mui/styles/withStyles";
import makeStyles from "@mui/styles/makeStyles";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import MuiDialogTitle from "@mui/material/DialogTitle";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";

import ReactJson from "react-json-view";
import { grey } from "@mui/material/colors";
import Button from "../Button";

import * as sourceActions from "../../ducks/source";
import * as gcnEventActions from "../../ducks/gcnEvent";
import * as shiftActions from "../../ducks/shift";
import * as earthquakeActions from "../../ducks/earthquake";

const useStyles = makeStyles((theme) => ({
  linkButton: {
    textDecoration: "none",
    color: theme.palette.info.dark,
    fontWeight: "bold",
    verticalAlign: "baseline",
    backgroundColor: "transparent",
    border: "none",
    cursor: "pointer",
    display: "inline",
    margin: 0,
    padding: 0,
    "&:hover": {
      textDecoration: "underline",
    },
  },
  dialogContent: {
    padding: theme.spacing(2),
    width: "100%",
    minWidth: "15rem",

    // Override styling in react-file-previewer
    "& img": {
      maxWidth: theme.breakpoints.values.md - theme.spacing(10),
    },
    "& canvas": {
      maxWidth: theme.breakpoints.values.md - theme.spacing(10),
      height: "auto !important",
    },
  },
  filename: {
    marginBottom: theme.spacing(1),
  },
  unsupportedType: {
    width: "20rem",
    border: "1px solid lightgray",
    padding: theme.spacing(1),
  },
  textArea: {
    width: "100%",
    height: "50vh",
  },
  attachmentPreview: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
    height: "100%",
  },
}));

const VIDEO_EXTENSION_TO_TYPE = {
  mp4: "video/mp4",
  ogg: "video/ogg",
  ogv: "video/ogg",
  webm: "video/webm",
};
const AUDIO_EXTENSION_TO_TYPE = {
  aac: "audio/aac",
  mp3: "audio/mpeg",
  oga: "audio/ogg",
  wav: "audio/wav",
};
const IMAGE_EXTENSION_TO_TYPE = {
  apng: "image/apng",
  avif: "image/avif",
  bmp: "image/bmp",
  gif: "image/gif",
  ico: "image/x-icon",
  jpeg: "image/jpeg",
  jpg: "image/jpeg",
  png: "image/png",
  svg: "image/svg+xml",
  webp: "image/webp",
};
const SUPPORTED_VIDEO_TYPES = Object.keys(VIDEO_EXTENSION_TO_TYPE);
const SUPPORTED_AUDIO_TYPES = Object.keys(AUDIO_EXTENSION_TO_TYPE);
const SUPPORTED_IMAGE_TYPES = Object.keys(IMAGE_EXTENSION_TO_TYPE);
const SUPPORTED_TEXT_TYPES = [
  "txt",
  "log",
  "logs",
  "csv",
  "tsv",
  "htm",
  "html",
  "js",
  "mjs",
  "json",
  "xml",
];
const SUPPORTED_FITS_TYPES = ["fit", "fits", "fz"];

const SUPPORTED_TYPES = [
  ...SUPPORTED_AUDIO_TYPES,
  ...SUPPORTED_VIDEO_TYPES,
  ...SUPPORTED_IMAGE_TYPES,
  ...SUPPORTED_TEXT_TYPES,
  ...SUPPORTED_FITS_TYPES,
  "pdf",
];

const dialogTitleStyles = (theme) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  title: {
    marginRight: theme.spacing(2),
  },
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(dialogTitleStyles)(
  ({ children, classes, onClose }) => (
    <MuiDialogTitle disableTypography className={classes.root}>
      <Typography variant="h6" className={classes.title}>
        {children}
      </Typography>
      {onClose ? (
        <IconButton
          aria-label="close"
          className={classes.closeButton}
          onClick={onClose}
          size="large"
        >
          <CloseIcon />
        </IconButton>
      ) : null}
    </MuiDialogTitle>
  ),
);

export const shortenFilename = (filename) => {
  if (filename.length <= 15) {
    return filename;
  }
  if (filename.includes(".")) {
    const extensionLength = filename.split(".", 2)[1].length;
    // Where the ellipsis should start - either at character 12, or the extension
    // plus an additional 5 characters into the basename (whichever is earlier)
    const firstEnd = Math.min(12, filename.length - extensionLength - 6);
    return `${filename.slice(0, firstEnd)}...${filename.slice(
      -extensionLength - 5,
    )}`;
  }

  return `${filename.slice(0, 12)}...`;
};

const readJsonFile = (commentAttachment, commentId) => {
  let jsonFile = {};
  try {
    jsonFile =
      commentId === commentAttachment?.commentId
        ? JSON.parse(commentAttachment.attachment)
        : {};
  } catch (e) {
    jsonFile = {
      "JSON Preview Parsing Error": `${e.message}. Please download the file if you want to inspect it.`,
    };
  }
  return jsonFile;
};

const readTextFile = (commentAttachment, commentId) => {
  let txtFile = "";
  try {
    txtFile =
      commentId === commentAttachment?.commentId
        ? commentAttachment.attachment
        : "";
  } catch (e) {
    txtFile = `Error reading text file: ${e.message}`;
  }
  return txtFile;
};

const CommentAttachmentPreview = ({
  filename,
  commentId,
  associatedResourceType,
  objectID = null,
  gcnEventID = null,
  shiftID = null,
  earthquakeID = null,
}) => {
  const classes = useStyles();
  const theme = useTheme();
  const darkTheme = theme.palette.mode === "dark";
  const dispatch = useDispatch();

  function resourceType(state) {
    let type = "";
    if (associatedResourceType === "gcn_event") {
      type = state.gcnEvent.commentAttachment;
    } else if (associatedResourceType === "shift") {
      type = state.shift.commentAttachment;
    } else if (associatedResourceType === "earthquake") {
      type = state.earthquake.commentAttachment;
    } else {
      type = state.source.commentAttachment;
    }
    return type;
  }

  const commentAttachment = useSelector((state) => resourceType(state));
  const [open, setOpen] = useState(false);

  const getURLs = () => {
    let baseUrl = "";
    if (associatedResourceType === "gcn_event") {
      baseUrl = `/api/${associatedResourceType}/${gcnEventID}/comments/${commentId}/attachment`;
    } else if (associatedResourceType === "shift") {
      baseUrl = `/api/${associatedResourceType}/${shiftID}/comments/${commentId}/attachment`;
    } else if (associatedResourceType === "earthquake") {
      baseUrl = `/api/${associatedResourceType}/${earthquakeID}/comments/${commentId}/attachment`;
    } else {
      baseUrl = `/api/${associatedResourceType}/${objectID}/comments/${commentId}/attachment`;
    }
    return {
      previewUrl: `${baseUrl}?preview=True&download=False`,
      url: baseUrl,
    };
  };

  const fileType = filename.includes(".")
    ? filename.split(".").pop().toLowerCase()
    : "";

  useEffect(() => {
    if (
      SUPPORTED_TEXT_TYPES.includes(fileType) &&
      commentId !== commentAttachment?.commentId &&
      open
    ) {
      if (associatedResourceType === "sources") {
        dispatch(sourceActions.getCommentTextAttachment(objectID, commentId));
      } else if (associatedResourceType === "spectra") {
        dispatch(
          sourceActions.getCommentOnSpectrumTextAttachment(objectID, commentId),
        );
      } else if (associatedResourceType === "gcn_event") {
        dispatch(
          gcnEventActions.getCommentOnGcnEventTextAttachment(
            gcnEventID,
            commentId,
          ),
        );
      } else if (associatedResourceType === "earthquake") {
        dispatch(
          earthquakeActions.getCommentOnEarthquakeTextAttachment(
            earthquakeID,
            commentId,
          ),
        );
      } else if (associatedResourceType === "shift") {
        dispatch(
          shiftActions.getCommentOnShiftTextAttachment(shiftID, commentId),
        );
      }
    }
  }, [open]);

  const handleClickOpen = () => {
    if (fileType === "pdf") {
      window.open(getURLs().previewUrl, "_blank");
      return;
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  return (
    <div>
      <Tooltip title={filename}>
        <div>
          Attachment:&nbsp;
          <button
            type="button"
            className={classes.linkButton}
            onClick={handleClickOpen}
            data-testid={`attachmentButton_${filename.split(".")[0]}`}
          >
            {shortenFilename(filename)}
          </button>
        </div>
      </Tooltip>
      {open && (
        <Dialog
          open={open}
          onClose={handleClose}
          style={{ position: "fixed" }}
          maxWidth="xlg"
          fullWidth={
            SUPPORTED_TYPES.includes(fileType) &&
            !SUPPORTED_AUDIO_TYPES.includes(fileType)
          }
        >
          <DialogTitle onClose={handleClose}>Attachment Preview</DialogTitle>
          <DialogContent dividers>
            <div className={classes.dialogContent}>
              <Typography variant="subtitle1" className={classes.filename}>
                {filename}
              </Typography>
              <div className={classes.attachmentPreview}>
                {fileType === "json" && (
                  <ReactJson
                    src={readJsonFile(commentAttachment, commentId)}
                    name={false}
                    theme={darkTheme ? "monokai" : "rjv-default"}
                  />
                )}
                {SUPPORTED_TEXT_TYPES.includes(fileType) &&
                  fileType !== "json" && (
                    <textarea
                      className={classes.textArea}
                      value={readTextFile(commentAttachment, commentId)}
                      readOnly
                    />
                  )}
                {SUPPORTED_VIDEO_TYPES.includes(fileType) &&
                  VIDEO_EXTENSION_TO_TYPE[fileType] && (
                    <video
                      controls
                      style={{
                        height: "68vh",
                        maxWidth: "100%",
                        width: "auto",
                      }}
                    >
                      <source
                        src={getURLs().previewUrl}
                        type={VIDEO_EXTENSION_TO_TYPE[fileType]}
                      />
                      <track kind="captions" />
                      Your browser does not support the video tag.
                    </video>
                  )}
                {SUPPORTED_AUDIO_TYPES.includes(fileType) &&
                  AUDIO_EXTENSION_TO_TYPE[fileType] && (
                    <audio controls>
                      <source
                        src={getURLs().previewUrl}
                        type={AUDIO_EXTENSION_TO_TYPE[fileType]}
                      />
                      <track kind="captions" />
                      Your browser does not support the audio element.
                    </audio>
                  )}
                {[...SUPPORTED_IMAGE_TYPES, ...SUPPORTED_FITS_TYPES].includes(
                  fileType,
                ) && (
                  <img
                    src={getURLs().previewUrl}
                    alt={filename}
                    style={{
                      height: "68vh",
                      maxWidth: "100%",
                      width: "auto",
                    }}
                  />
                )}
                {!SUPPORTED_TYPES.includes(fileType) && (
                  <div className={classes.unsupportedType}>
                    Previews are unavailable for {fileType.toUpperCase()} files.
                  </div>
                )}
              </div>
            </div>
          </DialogContent>
          <DialogActions>
            <div>
              <Button
                primary
                size="large"
                endIcon={<CloudDownloadIcon />}
                href={getURLs(fileType).url}
                onClick={handleClose}
                data-testid={`attachmentDownloadButton_${
                  filename.split(".")[0]
                }`}
                style={{ marginBottom: "10px" }}
              >
                Download file
              </Button>
            </div>
          </DialogActions>
        </Dialog>
      )}
    </div>
  );
};

CommentAttachmentPreview.propTypes = {
  filename: PropTypes.string.isRequired,
  objectID: PropTypes.string,
  gcnEventID: PropTypes.number,
  earthquakeID: PropTypes.string,
  shiftID: PropTypes.number,
  commentId: PropTypes.number.isRequired,
  associatedResourceType: PropTypes.string.isRequired,
};

CommentAttachmentPreview.defaultProps = {
  objectID: null,
  gcnEventID: null,
  earthquakeID: null,
  shiftID: null,
};

export default CommentAttachmentPreview;
