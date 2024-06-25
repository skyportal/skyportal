import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";

import EditIcon from "@mui/icons-material/Edit";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import makeStyles from "@mui/styles/makeStyles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import * as sourceActions from "../../ducks/source";

dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
  text: {
    margin: 0,
    padding: 0,
  },
}));

const UpdateSourceTNS = ({ source }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [dialogOpen, setDialogOpen] = useState(false);

  const handleSubmit = async ({ formData }) => {
    dispatch(sourceActions.addTNS(source.id, formData)).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification("Successfully queried TNS"));
      } else {
        dispatch(showNotification("Failed to query TNS", "error"));
      }
    });
  };

  const tnsFormSchema = {
    type: "object",
    properties: {
      radius: {
        type: "number",
        title: "Search radius [arcsec]",
        default: 2.0,
      },
    },
  };

  return (
    <>
      <IconButton
        data-testid="updateTNSIconButton"
        onClick={() => {
          setDialogOpen(true);
        }}
        size="small"
      >
        <EditIcon size="small" className={classes.editIcon} />
      </IconButton>
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>{`Query TNS for an object's name`}</DialogTitle>
        <DialogContent>
          <div>
            <Form
              schema={tnsFormSchema}
              validator={validator}
              onSubmit={handleSubmit}
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

UpdateSourceTNS.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    tns_name: PropTypes.string,
  }).isRequired,
};

export default UpdateSourceTNS;
