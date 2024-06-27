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

const UpdateSourceGCNCrossmatch = ({ source }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  let firstDet = source?.photstats[0]?.first_detected_mjd;
  if (firstDet !== undefined && firstDet !== null) {
    firstDet = dayjs.unix((firstDet + 2400000.5 + 0.5 - 2440588) * 86400);
  }

  const [dialogOpen, setDialogOpen] = useState(false);
  const defaultStartDate = firstDet
    ? firstDet.subtract(2, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ")
    : dayjs().subtract(3, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = firstDet
    ? firstDet.add(5, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ")
    : dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");

  const handleSubmit = async ({ formData }) => {
    dispatch(sourceActions.addGCNCrossmatch(source.id, formData)).then(
      (response) => {
        if (response.status === "success") {
          dispatch(
            showNotification(
              "Successfully triggered GCN crossmatch. Please be patient.",
            ),
          );
        } else {
          dispatch(
            showNotification("Failed to trigger the GCN crossmatch.", "error"),
          );
        }
      },
    );
  };

  const gcnFormSchema = {
    type: "object",
    properties: {
      startDate: {
        type: "string",
        format: "date-time",
        title: "Start Date [UTC Time]",
        default: defaultStartDate,
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "End Date [UTC Time]",
        default: defaultEndDate,
      },
      probability: {
        type: "number",
        title: "Cumulative Probability",
        default: 0.95,
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
        <DialogTitle>Query GCN Event Crossmatch</DialogTitle>
        <DialogContent>
          <div>
            <Form
              schema={gcnFormSchema}
              validator={validator}
              onSubmit={handleSubmit}
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

UpdateSourceGCNCrossmatch.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    photstats: PropTypes.arrayOf(
      PropTypes.shape({
        first_detected_mjd: PropTypes.number,
      }),
    ),
  }).isRequired,
};

export default UpdateSourceGCNCrossmatch;
