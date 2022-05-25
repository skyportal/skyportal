import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import { withStyles, makeStyles, useTheme } from "@material-ui/core/styles";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogActions from "@material-ui/core/DialogActions";
import MuiDialogTitle from "@material-ui/core/DialogTitle";
import Button from "@material-ui/core/Button";
import CloudDownloadIcon from "@material-ui/icons/CloudDownload";
import IconButton from "@material-ui/core/IconButton";
import CloseIcon from "@material-ui/icons/Close";
import Typography from "@material-ui/core/Typography";
import Tooltip from "@material-ui/core/Tooltip";
import grey from "@material-ui/core/colors/grey";

import FilePreviewer, { FilePreviewerThumbnail } from "react-file-previewer";
import ReactJson from "react-json-view";

import * as sourceActions from "../ducks/source";
import * as gcnEventActions from "../ducks/gcnEvent";
import * as shiftActions from "../ducks/shift";

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
}));

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
        >
          <CloseIcon />
        </IconButton>
      ) : null}
    </MuiDialogTitle>
  )
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
      -extensionLength - 5
    )}`;
  }

  return `${filename.slice(0, 12)}...`;
};

const CommentAttachmentPreview = ({
  filename,
  commentId,
  associatedResourceType,
  objectID = null,
  gcnEventID = null,
  shiftID = null,
}) => {
  const classes = useStyles();
  const theme = useTheme();
  const darkTheme = theme.palette.type === "dark";

  function resourceType(state) {
    let type = "";
    if (associatedResourceType === "gcn_event") {
      type = state.gcnEvent.commentAttachment;
    } else if (associatedResourceType === "shift") {
      type = state.shift.commentAttachment;
    } else {
      type = state.source.commentAttachment;
    }
    return type;
  }

  const dispatch = useDispatch();
  const commentAttachment = useSelector((state) => resourceType(state));
  const cachedAttachmentCommentId = commentAttachment
    ? commentAttachment.commentId
    : null;
  const isCached = commentId === cachedAttachmentCommentId;

  const [open, setOpen] = useState(false);
  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const fileType = filename.includes(".") ? filename.split(".").pop() : "";
  const supportedType = ["png", "jpg", "jpeg", "pdf", "gif", "json"].includes(
    fileType.toLowerCase()
  );

  let jsonFile = {};
  try {
    jsonFile = isCached
      ? JSON.parse(Object.entries(commentAttachment)[1][1])
      : {};
  } catch (e) {
    jsonFile = {
      "JSON Preview Parsing Error": `${e.message}. Please download the file if you want to inspect it.`,
    };
  }

  if (fileType.toLowerCase() === "json" && !isCached && open) {
    if (associatedResourceType === "sources") {
      dispatch(sourceActions.getCommentAttachmentPreview(objectID, commentId));
    } else if (associatedResourceType === "spectra") {
      dispatch(
        sourceActions.getCommentOnSpectrumAttachmentPreview(objectID, commentId)
      );
    } else if (associatedResourceType === "gcn_event") {
      dispatch(
        gcnEventActions.getCommentOnGcnEventAttachmentPreview(
          gcnEventID,
          commentId
        )
      );
    } else if (associatedResourceType === "shift") {
      dispatch(
        shiftActions.getCommentOnShiftAttachmentPreview(shiftID, commentId)
      );
    }
  }

  let baseUrl = "";
  // The FilePreviewer expects a url ending with .pdf for PDF files
  if (associatedResourceType === "gcn_event") {
    baseUrl = `/api/${associatedResourceType}/${gcnEventID}/comments/${commentId}/attachment`;
  } else if (associatedResourceType === "shift") {
    baseUrl = `/api/${associatedResourceType}/${shiftID}/comments/${commentId}/attachment`;
  } else {
    baseUrl = `/api/${associatedResourceType}/${objectID}/comments/${commentId}/attachment`;
  }
  const url = fileType === "pdf" ? `${baseUrl}.pdf` : baseUrl;

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
          maxWidth="md"
        >
          <DialogTitle onClose={handleClose}>Attachment Preview</DialogTitle>
          <DialogContent dividers>
            <div className={classes.dialogContent}>
              <Typography variant="subtitle1" className={classes.filename}>
                {filename}
              </Typography>
              {supportedType && fileType === "pdf" && (
                // Using FilePreviewerThumbnail results with PDF in very small
                // preview with no way to edit it without losing resolution due
                // to hard-coded in-line styling, so use the FilePreviewer
                // component for PDF
                <FilePreviewer file={{ url }} hideControls />
              )}
              {supportedType && fileType === "json" && (
                <ReactJson
                  src={jsonFile}
                  name={false}
                  theme={darkTheme ? "monokai" : "rjv-default"}
                />
              )}
              {supportedType && fileType !== "pdf" && fileType !== "json" && (
                <FilePreviewerThumbnail file={{ url }} hideControls />
              )}
              {!supportedType && (
                <div className={classes.unsupportedType}>
                  Previews are unavailable for {fileType.toUpperCase()} files.
                </div>
              )}
            </div>
          </DialogContent>
          <DialogActions>
            <div>
              <Button
                color="primary"
                size="large"
                endIcon={<CloudDownloadIcon />}
                href={url}
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
  shiftID: PropTypes.number,
  commentId: PropTypes.number.isRequired,
  associatedResourceType: PropTypes.string.isRequired,
};

CommentAttachmentPreview.defaultProps = {
  objectID: null,
  gcnEventID: null,
  shiftID: null,
};

export default CommentAttachmentPreview;
