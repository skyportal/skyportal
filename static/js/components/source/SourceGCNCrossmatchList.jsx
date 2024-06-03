import React, { useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import Button from "../Button";

const useStyles = makeStyles(() => ({
  row: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
}));

const SourceGCNCrossmatchList = ({ gcn_crossmatches }) => {
  const classes = useStyles();
  const [dialogOpen, setDialogOpen] = useState(false);

  if (gcn_crossmatches?.length > 1) {
    // show just the latest crossmatch, and a plus button to show the dialog with all of them
    return (
      <>
        <div className={classes.row}>
          <Link
            to={`/gcn_events/${gcn_crossmatches[0].replace(" ", "T")}`}
            role="link"
            key={gcn_crossmatches[0]}
          >
            <Button size="small" style={{ margin: 0, padding: 0 }}>
              {gcn_crossmatches[0]}
            </Button>
          </Link>
          <IconButton
            size="small"
            data-testid="addGcnEventAliasIconButton"
            onClick={() => {
              setDialogOpen(true);
            }}
            style={{ padding: 0, margin: 0 }}
          >
            <AddIcon fontSize="small" style={{ fontSize: "1rem" }} />
          </IconButton>
        </div>
        <Dialog
          open={dialogOpen}
          onClose={() => {
            setDialogOpen(false);
          }}
          style={{ position: "fixed" }}
        >
          <DialogTitle>GCN Event Crossmatch</DialogTitle>
          <DialogContent>
            {gcn_crossmatches && (
              <div>
                {gcn_crossmatches.map((dateobs) => (
                  <div key={dateobs}>
                    <Link
                      to={`/gcn_events/${dateobs.replace(" ", "T")}`}
                      role="link"
                      key={dateobs}
                    >
                      <Button size="small">{dateobs}</Button>
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </>
    );
  }
  if (gcn_crossmatches?.length === 1) {
    return (
      <Link
        to={`/gcn_events/${gcn_crossmatches[0].replace(" ", "T")}`}
        role="link"
        key={gcn_crossmatches[0]}
      >
        <Button size="small" style={{ margin: 0, padding: 0 }}>
          {gcn_crossmatches[0]}
        </Button>
      </Link>
    );
  }
  return <></>;
};

SourceGCNCrossmatchList.propTypes = {
  gcn_crossmatches: PropTypes.arrayOf(PropTypes.string).isRequired,
};

export default SourceGCNCrossmatchList;
