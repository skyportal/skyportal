import React, { useState } from "react";
import PropTypes from "prop-types";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import BuildIcon from "@mui/icons-material/Build";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ImageAspectRatioIcon from "@mui/icons-material/ImageAspectRatio";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

import { STATUS_COLORS } from "./constants";
import { dec_to_dms, ra_to_hours } from "../units";
import { Link } from "react-router-dom";
import AssignmentForm from "../components/observing_run/AssignmentForm";
import Box from "@mui/material/Box";

export const renderTargetName = (item) => {
  const objId = item.obj.id;
  return (
    <Link primary to={`/source/${objId}`}>
      {objId}
    </Link>
  );
};

export const renderStatus = (item) => {
  const match = Object.keys(STATUS_COLORS).find((key) =>
    item.status.startsWith(key),
  );
  const color = STATUS_COLORS[match] || "grey";
  return (
    <Box
      sx={{
        backgroundColor: color,
        color: "white",
        padding: "0.4rem 0.7rem",
        borderRadius: "1rem",
        width: "fit-content",
      }}
    >
      {item.status}
    </Box>
  );
};

export const renderRA = (item) => {
  return (
    <div>
      {item.obj.ra}
      <br />
      {ra_to_hours(item.obj.ra)}
    </div>
  );
};

export const renderDec = (item) => {
  return (
    <div>
      {item.obj.dec}
      <br />
      {dec_to_dms(item.obj.dec)}
    </div>
  );
};

export const renderFinderButton = (item) => {
  return (
    <>
      <IconButton
        size="small"
        color="primary"
        component="a"
        href={`/api/sources/${item.obj.id}/finder`}
        download
      >
        <PictureAsPdfIcon />
      </IconButton>
      <Link
        to={`/source/${item.obj.id}/finder`}
        rel="noopener noreferrer"
        target="_blank"
      >
        <IconButton size="small" color="primary">
          <ImageAspectRatioIcon />
        </IconButton>
      </Link>
    </>
  );
};

export const renderRise = (item) =>
  item.rise_time_utc
    ? new Date(item.rise_time_utc).toLocaleTimeString()
    : "Never up";

export const renderSet = (item) =>
  item.set_time_utc
    ? new Date(item.set_time_utc).toLocaleTimeString()
    : "Never up";

export const ActionsMenu = ({
  item,
  updateFunction,
  observingRunList = null,
}) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const menuItemProps = (menuItemStatus, statusColor, isLast = false) => ({
    onClick: () => {
      setAnchorEl(null);
      updateFunction(item, menuItemStatus);
    },
    disabled: item.status.startsWith(menuItemStatus),
    divider: !isLast,
    sx: {
      color: item.status.startsWith(menuItemStatus) ? "grey" : statusColor,
    },
  });

  const reassignAssignment = () => () => {
    setAnchorEl(null);
    setDialogOpen(true);
  };

  return (
    <div>
      <IconButton
        aria-controls="actions-menu"
        aria-haspopup="true"
        onClick={(e) => setAnchorEl(e.currentTarget)}
        size="large"
        color="primary"
      >
        <BuildIcon />
      </IconButton>
      <Menu
        id="actions-menu"
        anchorEl={anchorEl}
        keepMounted
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
      >
        <MenuItem {...menuItemProps("complete", STATUS_COLORS.complete)}>
          Mark as observed
        </MenuItem>
        <MenuItem
          {...menuItemProps("not observed", STATUS_COLORS["not observed"])}
        >
          Mark as not observed
        </MenuItem>
        <MenuItem
          {...menuItemProps(
            "pending",
            STATUS_COLORS.pending,
            item.status !== "complete" &&
              item.status !== "not observed" &&
              !observingRunList,
          )}
        >
          Mark as pending
        </MenuItem>
        {item.status === "not observed" && observingRunList && (
          <MenuItem onClick={reassignAssignment()} color="primary">
            <Typography color="primary" fontWeight="bold">
              Reassign
            </Typography>
          </MenuItem>
        )}
        {item.status === "complete" && [
          <MenuItem
            divider
            component={Link}
            to={`/upload_spectrum/${item.obj.id}`}
            color="primary"
            key="upload-spectrum"
          >
            <Typography color="primary" fontWeight="bold">
              Upload Spectrum
            </Typography>
          </MenuItem>,
          <MenuItem
            component={Link}
            to={`/upload_photometry/${item.obj.id}`}
            color="primary"
            key="upload-photometry"
          >
            <Typography color="primary" fontWeight="bold">
              Upload Photometry
            </Typography>
          </MenuItem>,
        ]}
      </Menu>
      {observingRunList && (
        <Dialog
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          maxWidth="md"
        >
          <DialogTitle>Reassign to Observing Run</DialogTitle>
          <DialogContent dividers>
            <AssignmentForm
              obj_id={item.obj.id}
              observingRunList={observingRunList}
            />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

ActionsMenu.propTypes = {
  item: PropTypes.shape({
    status: PropTypes.string,
    id: PropTypes.number,
    obj: PropTypes.shape({
      id: PropTypes.string,
    }).isRequired,
  }).isRequired,
  updateFunction: PropTypes.func.isRequired,
  observingRunList: PropTypes.arrayOf(PropTypes.shape({})),
};
