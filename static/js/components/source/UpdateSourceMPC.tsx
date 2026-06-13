import { useState } from "react";
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
import { useAddMPCMutation } from "../../ducks/source";
import { useAppDispatch } from "../../types/hooks";

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

interface UpdateSourceMPCProps {
  source: {
    id: string;
    mpc_name?: string;
    first_detected?: string;
    [key: string]: any;
  };
}

const UpdateSourceMPC = ({ source }: UpdateSourceMPCProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [addMPC] = useAddMPCMutation();

  const [dialogOpen, setDialogOpen] = useState(false);
  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ss");
  const defaultDate = source.first_detected ? source.first_detected : nowDate;

  const handleSubmit = async ({ formData }: { formData: any }) => {
    try {
      await addMPC({ id: source.id, formData }).unwrap();
      dispatch(showNotification("Successfully queried the MPC"));
    } catch {
      dispatch(showNotification("Failed to query the MPC", "error"));
    }
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
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Query MPC</DialogTitle>
        <DialogContent>
          <div>
            <Form
              schema={mpcFormSchema as any}
              validator={validator}
              onSubmit={handleSubmit as any}
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UpdateSourceMPC;
