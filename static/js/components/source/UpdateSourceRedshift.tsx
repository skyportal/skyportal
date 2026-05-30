import React, { useEffect, useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { makeStyles } from "tss-react/mui";
import SaveIcon from "@mui/icons-material/Save";
import ClearIcon from "@mui/icons-material/Clear";
import Tooltip from "@mui/material/Tooltip";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import * as sourceActions from "../../ducks/source";

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

interface UpdateSourceRedshiftProps {
  source: {
    id?: string;
    redshift?: number | null;
    redshift_error?: number | null;
    redshift_origin?: string | null;
    [key: string]: any;
  };
}

const UpdateSourceRedshift = ({ source }: UpdateSourceRedshiftProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [state, setState] = useState<Record<string, any>>({
    redshift: source.redshift ? String(source.redshift) : "",
    redshift_error: source.redshift_error ? String(source.redshift_error) : "",
    redshift_origin: source.redshift_origin
      ? String(source.redshift_origin)
      : "",
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(
      !String(source.redshift) || isNaN(String(source.redshift) as any),
    );
    setState({
      redshift: source.redshift ? String(source.redshift) : "",
      redshift_error: source.redshift_error
        ? String(source.redshift_error)
        : "",
      redshift_origin: source.redshift_origin
        ? String(source.redshift_origin)
        : "",
    });
  }, [source, setInvalid]);

  const handleChange = (e: any) => {
    const newState: Record<string, any> = {};
    newState[e.target.name] = e.target.value;
    const value = String(e.target.value).trim();
    if (e.target.name === "redshift") {
      setInvalid(!value || isNaN(value as any));
    }
    setState({
      ...state,
      ...newState,
    });
  };

  const handleSubmit = async (subState: any) => {
    setIsSubmitting(true);
    const newState: Record<string, any> = {};
    newState.redshift = subState.redshift ? subState.redshift : null;
    newState.redshift_error = subState.redshift_error
      ? subState.redshift_error
      : null;
    newState.redshift_origin = subState.redshift_origin
      ? subState.redshift_origin
      : null;
    const result: any = await dispatch(
      sourceActions.updateSource(source.id, {
        ...newState,
      }),
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("Source redshift successfully updated."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <EditIcon
        data-testid="updateRedshiftIconButton"
        fontSize="small"
        className={classes.editIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Update Redshift</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a valid float" />
            )}
            <TextField
              data-testid="updateRedshiftTextfield"
              size="small"
              label="z"
              value={state.redshift}
              name="redshift"
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <p />
          <div>
            <TextField
              data-testid="updateRedshiftErrorTextfield"
              size="small"
              label="z_err"
              value={state.redshift_error}
              name="redshift_error"
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <p />
          <div>
            <TextField
              data-testid="updateRedshiftOriginTextfield"
              size="small"
              label="z_origin (optional)"
              value={state.redshift_origin}
              name="redshift_origin"
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => {
                handleSubmit(state);
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="updateRedshiftSubmitButton"
              disabled={isSubmitting || invalid}
            >
              Save
            </Button>
          </div>
          <div className={classes.saveButton}>
            <Tooltip title="Clear source redshift value (set to null)">
              <span>
                <Button
                  primary
                  onClick={() => {
                    handleSubmit({
                      redshift: null,
                      redshift_error: null,
                      redshift_origin: null,
                    });
                  }}
                  endIcon={<ClearIcon />}
                  size="large"
                  data-testid="nullifyRedshiftButton"
                  disabled={isSubmitting || source.redshift === null}
                >
                  Clear
                </Button>
              </span>
            </Tooltip>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UpdateSourceRedshift;
