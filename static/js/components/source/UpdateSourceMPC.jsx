import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import EditIcon from "@mui/icons-material/Edit";
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
}));

const UpdateSourceMPC = ({ source }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [dialogOpen, setDialogOpen] = useState(false);
  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ss");
  const defaultDate = source.first_detected ? source.first_detected : nowDate;

  const handleSubmit = async ({ formData }) => {
    dispatch(sourceActions.addMPC(source.id, formData)).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification("Successfully queried the MPC"));
      } else {
        dispatch(showNotification("Failed to query the MPC", "error"));
      }
    });
  };

  const mpcFormSchema = {
    type: "object",
    properties: {
      date: {
        type: "string",
        format: "date-time",
        title: "Start Date [UTC]",
        default: defaultDate,
      },
      search_radius: {
        type: "number",
        title: "Search Radius [arcmin]",
        default: 1,
      },
      limiting_magnitude: {
        type: "number",
        title: "Limiting Magnitude [mag]",
        default: 24.0,
      },
      obscode: {
        type: "string",
        title: "Minor planet center observatory code",
        default: "500",
      },
    },
  };

  return (
    <>
      <EditIcon
        data-testid="updateMPCIconButton"
        fontSize="small"
        className={classes.editIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Query MPC</DialogTitle>
        <DialogContent>
          <div>
            <Form
              schema={mpcFormSchema}
              validator={validator}
              onSubmit={handleSubmit}
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

UpdateSourceMPC.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    mpc_name: PropTypes.string,
    first_detected: PropTypes.string,
  }).isRequired,
};

export default UpdateSourceMPC;
