import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";

import { withStyles } from "@material-ui/core/styles";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogActions from "@material-ui/core/DialogActions";
import MuiDialogTitle from "@material-ui/core/DialogTitle";
import Button from "@material-ui/core/Button";
import VisibilityIcon from "@material-ui/icons/Visibility";
import KeyboardArrowRightIcon from "@material-ui/icons/KeyboardArrowRight";
import Chip from "@material-ui/core/Chip";
import IconButton from "@material-ui/core/IconButton";
import CloseIcon from "@material-ui/icons/Close";
import Typography from "@material-ui/core/Typography";

import ThumbnailList from "./ThumbnailList";
import ShowClassification from "./ShowClassification";
import * as Action from "../ducks/source";
import { ra_to_hours, dec_to_hours } from "../units";
import styles from "./SourceQuickView.css";

const dialogTitleStyles = (theme) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: theme.palette.grey[500],
  },
});

const DialogTitle = withStyles(dialogTitleStyles)((props) => {
  const { children, classes, onClose } = props;
  return (
    <MuiDialogTitle disableTypography className={classes.root}>
      <Typography variant="h4">{children}</Typography>
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
  );
});

const getDialogContentDiv = (source, isCached, taxonomyList) => {
  if (source.loadError) {
    return <div>{source.loadError}</div>;
  }

  if (!isCached) {
    return (
      <div>
        <span>Loading...</span>
      </div>
    );
  }

  return (
    <div id="source-quick-view-dialog-content" className={styles.dialogContent}>
      <ThumbnailList
        ra={source.ra}
        dec={source.dec}
        thumbnails={source.thumbnails}
      />
      <div className={styles.textContent}>
        <ShowClassification
          classifications={source.classifications}
          taxonomyList={taxonomyList}
        />
        <div className={styles.textContentItem}>
          <b>Position (J2000):</b>
          &nbsp;
          <br />
          {source.ra}, {source.dec} (&alpha;, &delta; =&nbsp;
          {ra_to_hours(source.ra)}, {dec_to_hours(source.dec)})
        </div>
        <div className={styles.textContentItem}>
          <b>Redshift: &nbsp;</b>
          {source.redshift}
        </div>
        <div className={styles.textContentItem}>
          <b>Groups: &nbsp;</b>
          {source.groups.map((group) => (
            <Chip
              label={group.name.substring(0, 15)}
              key={group.id}
              size="small"
              className={styles.chip}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

const SourceQuickView = ({ sourceId, className }) => {
  const dispatch = useDispatch();

  const [open, setOpen] = useState(false);
  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const source = useSelector((state) => state.source);
  const cachedSourceId = source ? source.id : null;
  const isCached = sourceId === cachedSourceId;

  useEffect(() => {
    const fetchSource = async () => {
      dispatch(Action.fetchSource(sourceId));
    };

    if (!isCached && open) {
      fetchSource();
    }
  }, [dispatch, isCached, sourceId, open]);

  const { taxonomyList } = useSelector((state) => state.taxonomies);

  // Only load more detailed source info once dialog is opened
  if (open) {
    return (
      <div className={className}>
        <Button
          color="primary"
          variant="outlined"
          size="small"
          onClick={handleClickOpen}
          startIcon={<VisibilityIcon />}
          style={{ marginBottom: "10px" }}
        >
          QUICK VIEW
        </Button>
        <Dialog open={open} onClose={handleClose} style={{ position: "fixed" }}>
          <DialogTitle onClose={handleClose}>{source.id}</DialogTitle>
          <DialogContent dividers>
            {getDialogContentDiv(source, isCached, taxonomyList)}
          </DialogContent>
          <DialogActions>
            <div className={styles.sourceLinkButton}>
              <Link
                to={`/source/${source.id}`}
                style={{ textDecoration: "none" }}
                onClick={handleClose}
              >
                <Button
                  color="primary"
                  size="large"
                  endIcon={<KeyboardArrowRightIcon />}
                  style={{ marginBottom: "10px" }}
                >
                  GO TO SOURCE PAGE
                </Button>
              </Link>
            </div>
          </DialogActions>
        </Dialog>
      </div>
    );
  }

  return (
    <div className={className}>
      <Button
        color="primary"
        variant="outlined"
        size="small"
        onClick={handleClickOpen}
        startIcon={<VisibilityIcon />}
        style={{ marginBottom: "10px" }}
      >
        QUICK VIEW
      </Button>
    </div>
  );
};

SourceQuickView.propTypes = {
  sourceId: PropTypes.string.isRequired,
  className: PropTypes.string.isRequired,
};

export default SourceQuickView;
