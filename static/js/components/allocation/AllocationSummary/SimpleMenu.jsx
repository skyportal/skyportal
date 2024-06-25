import React from "react";
import { useDispatch } from "react-redux";
import { showNotification } from "baselayer/components/Notifications";
import IconButton from "@mui/material/IconButton";
import BuildIcon from "@mui/icons-material/Build";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Link from "@mui/material/Link";
import PropTypes from "prop-types";
import * as SourceAction from "../../../ducks/source";

const SimpleMenu = ({ request }) => {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const dispatch = useDispatch();

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const updateRequestStatus = async (status) => {
    handleClose();
    const result = await dispatch(
      SourceAction.editFollowupRequest({ status }, request.id),
    );
    if (result.status === "success") {
      dispatch(
        showNotification("Follow-up request status successfully updated"),
      );
    }
  };

  return (
    <div>
      <IconButton
        aria-controls="simple-menu"
        aria-haspopup="true"
        onClick={handleClick}
        variant="contained"
        size="large"
      >
        <BuildIcon />
      </IconButton>
      <Menu
        id="simple-menu"
        anchorEl={anchorEl}
        keepMounted
        open={Boolean(anchorEl)}
        onClose={handleClose}
      >
        {(request.status === "submitted" ||
          request.status === "not observed" ||
          request.status === "pending") && (
          <MenuItem
            onClick={() => updateRequestStatus("complete")}
            variant="contained"
            key={`${request.id}_done`}
          >
            Mark Observed
          </MenuItem>
        )}
        {(request.status === "submitted" ||
          request.status === "complete" ||
          request.status === "pending") && (
          <MenuItem
            onClick={() => updateRequestStatus("not observed")}
            variant="contained"
            key={`${request.id}_notdone`}
          >
            Mark Not Observed
          </MenuItem>
        )}
        {(request.status === "complete" ||
          request.status === "not observed") && (
          <MenuItem
            onClick={() => updateRequestStatus("pending")}
            variant="contained"
            key={`${request.id}_pending`}
          >
            Mark Pending
          </MenuItem>
        )}
        {request.status === "complete" && (
          <MenuItem key={`${request.id}_upload_spec`} onClick={handleClose}>
            <Link
              href={`/upload_spectrum/${request.obj.id}`}
              underline="none"
              color="textPrimary"
            >
              Upload Spectrum
            </Link>
          </MenuItem>
        )}
        {request.status === "complete" && (
          <MenuItem
            key={`${request.id}_upload_phot`}
            variant="contained"
            onClick={handleClose}
          >
            <Link
              href={`/upload_photometry/${request.obj.id}`}
              underline="none"
              color="textPrimary"
            >
              Upload Photometry
            </Link>
          </MenuItem>
        )}
      </Menu>
    </div>
  );
};

SimpleMenu.propTypes = {
  request: PropTypes.shape({
    status: PropTypes.string,
    id: PropTypes.number,
    obj: PropTypes.shape({
      id: PropTypes.string,
    }).isRequired,
  }).isRequired,
};

export default SimpleMenu;
