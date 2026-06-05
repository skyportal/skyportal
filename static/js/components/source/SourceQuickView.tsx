import { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import { Link } from "react-router-dom";

import { makeStyles } from "tss-react/mui";
import { withStyles } from "tss-react/mui";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import MuiDialogTitle from "@mui/material/DialogTitle";
import VisibilityIcon from "@mui/icons-material/Visibility";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import { grey } from "@mui/material/colors";
import Button from "../Button";

import ThumbnailList from "../thumbnail/ThumbnailList";
import ShowClassification from "../classification/ShowClassification";
import * as Action from "../../ducks/source";
import { useGetTaxonomiesQuery } from "../../ducks/taxonomies";
import { dec_to_dms, ra_to_hours } from "../../units";

const dialogTitleStyles = (theme: any) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(
  ({ children, classes, onClose }: any) => (
    <MuiDialogTitle component="div" className={classes.root}>
      <Typography variant="h4">{children}</Typography>
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
  dialogTitleStyles,
);

const useStyles = makeStyles()(() => ({
  textContent: {
    marginTop: "1rem",
    fontSize: "1.2em",
  },
  textContentItem: {
    padding: "0.375rem 0",
  },
  chip: {
    margin: "0.5em",
  },
  title: {
    fontSize: "1.5rem",
    fontWeight: "500",
    lineHeight: "1.6",
    letterSpacing: "0.0075em",
  },
  dialogContent: {
    padding: "1rem",
  },
  sourceLinkButton: {
    marginTop: "1rem",
    float: "right",
  },
}));

interface DialogContentDivProps {
  source: any;
  isCached: boolean;
  taxonomyList: any[];
}

const DialogContentDiv = ({
  source,
  isCached,
  taxonomyList,
}: DialogContentDivProps) => {
  const { classes } = useStyles();
  if (source.loadError) {
    return <div>{source.loadError}</div>;
  }

  if (!isCached) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <div
      data-testid="source-quick-view-dialog-content"
      className={classes.dialogContent}
    >
      <ThumbnailList
        ra={source.ra}
        dec={source.dec}
        thumbnails={source.thumbnails}
      />
      <div className={classes.textContent}>
        <ShowClassification
          classifications={source.classifications}
          taxonomyList={taxonomyList}
        />
        <div className={classes.textContentItem}>
          <b>Position (J2000):</b>
          &nbsp;
          <br />
          {source.ra}, {source.dec} (&alpha;, &delta; =&nbsp;
          {ra_to_hours(source.ra)}, {dec_to_dms(source.dec)})
        </div>
        <div className={classes.textContentItem}>
          <b>Redshift: &nbsp;</b>
          {source.redshift}
        </div>
        <div className={classes.textContentItem}>
          <b>Groups: &nbsp;</b>
          {source.groups.map((group: any) => (
            <Chip
              label={group.name.substring(0, 15)}
              key={group.id}
              size="small"
              className={classes.chip}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

interface SourceQuickViewProps {
  sourceId: string;
  className: string;
}

const SourceQuickView = ({ sourceId, className }: SourceQuickViewProps) => {
  const dispatch = useAppDispatch();
  const { classes } = useStyles();

  const [open, setOpen] = useState(false);
  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const source = useAppSelector((state) => state["source"]);
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

  const { data: taxonomyList = [] } = useGetTaxonomiesQuery();

  // Only load more detailed source info once dialog is opened
  if (open) {
    return (
      <div
        className={className}
        data-testid={`quickViewButton_${source.obj_id}`}
      >
        <Button
          primary
          size="small"
          onClick={handleClickOpen}
          endIcon={<VisibilityIcon />}
          style={{ marginBottom: "10px" }}
        >
          QUICK VIEW
        </Button>
        <Dialog open={open} onClose={handleClose} maxWidth="md">
          <DialogTitle onClose={handleClose}>{source.id}</DialogTitle>
          <DialogContent dividers>
            <DialogContentDiv
              source={source}
              isCached={isCached}
              taxonomyList={taxonomyList}
            />
          </DialogContent>
          <DialogActions>
            <div className={classes.sourceLinkButton}>
              <Link
                to={`/source/${source.id}`}
                style={{ textDecoration: "none" }}
                onClick={handleClose}
              >
                <Button
                  secondary
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
    <div className={className} data-testid={`quickViewButton_${source.obj_id}`}>
      <Button primary size="small" onClick={handleClickOpen}>
        QUICK VIEW
      </Button>
    </div>
  );
};

export default SourceQuickView;
