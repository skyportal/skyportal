import React, { useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import * as sourceActions from "../../ducks/source";

dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
}));

interface UpdateSourceGCNCrossmatchProps {
  source: {
    id?: string;
    photstats?: { first_detected_mjd?: number }[];
  };
}

const UpdateSourceGCNCrossmatch = ({
  source,
}: UpdateSourceGCNCrossmatchProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  let firstDet: any = source?.photstats?.[0]?.first_detected_mjd;
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

  const handleSubmit = async ({ formData }: { formData: any }) => {
    dispatch(sourceActions.addGCNCrossmatch(source.id, formData)).then(
      (response: any) => {
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
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Query GCN Event Crossmatch</DialogTitle>
        <DialogContent>
          <div>
            <Form
              schema={gcnFormSchema as any}
              validator={validator}
              onSubmit={handleSubmit as any}
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UpdateSourceGCNCrossmatch;
