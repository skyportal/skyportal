import { useEffect, useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { makeStyles } from "tss-react/mui";
import SaveIcon from "@mui/icons-material/Save";
import ClearIcon from "@mui/icons-material/Clear";
import Tooltip from "@mui/material/Tooltip";
import TextField from "@mui/material/TextField";
import { alpha } from "@mui/material/styles";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import { useUpdateSourceMutation } from "../../ducks/source";

const REDSHIFT_TYPES = [
  { value: "spectroscopic", label: "Spectroscopic" },
  { value: "photometric", label: "Photometric" },
];

const useStyles = makeStyles()((theme) => ({
  typeChoice: {
    display: "flex",
    gap: "0.5rem",
  },
  typeOption: {
    flex: 1,
    padding: "0.45rem 0.75rem",
    border: `1px solid ${theme.palette.divider}`,
    borderRadius: 6,
    background: "transparent",
    color: theme.palette.text.secondary,
    font: "inherit",
    fontSize: "0.875rem",
    cursor: "pointer",
    "&:hover": {
      borderColor: theme.palette.text.secondary,
    },
  },
  typeSelected: {
    borderColor: theme.palette.primary.main,
    background: alpha(theme.palette.primary.main, 0.08),
    color: theme.palette.primary.main,
    fontWeight: 600,
    "&:hover": {
      borderColor: theme.palette.primary.main,
    },
  },
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
    redshift_type?: string | null;
    [key: string]: any;
  };
}

const UpdateSourceRedshift = ({ source }: UpdateSourceRedshiftProps) => {
  const { classes, cx } = useStyles();
  const dispatch = useAppDispatch();
  const [updateSource] = useUpdateSourceMutation();
  const [state, setState] = useState<Record<string, any>>({
    redshift: source.redshift ? String(source.redshift) : "",
    redshift_error: source.redshift_error ? String(source.redshift_error) : "",
    redshift_origin: source.redshift_origin
      ? String(source.redshift_origin)
      : "",
    redshift_type: source.redshift_type ?? "",
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    if (dialogOpen) return;
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
      redshift_type: source.redshift_type ?? "",
    });
  }, [source, dialogOpen]);

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
    newState["redshift"] = subState.redshift ? subState.redshift : null;
    newState["redshift_error"] = subState.redshift_error
      ? subState.redshift_error
      : null;
    newState["redshift_origin"] = subState.redshift_origin
      ? subState.redshift_origin
      : null;
    newState["redshift_type"] = subState.redshift_type
      ? subState.redshift_type
      : null;
    try {
      await updateSource({
        id: source.id!,
        payload: { ...newState },
      }).unwrap();
      dispatch(showNotification("Source redshift successfully updated."));
      setDialogOpen(false);
    } catch {
      // error notification handled by the baseQuery
    }
    setIsSubmitting(false);
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
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Update Redshift</DialogTitle>
        <DialogContent style={{ paddingTop: "0.75rem" }}>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a valid float" />
            )}
            <TextField
              data-testid="updateRedshiftTextfield"
              size="small"
              fullWidth
              label="z"
              value={state["redshift"]}
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
              fullWidth
              label="z_err"
              value={state["redshift_error"]}
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
              fullWidth
              label="z_origin (optional)"
              value={state["redshift_origin"]}
              name="redshift_origin"
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <p />
          <div className={classes.typeChoice}>
            {REDSHIFT_TYPES.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                data-testid={`redshiftType_${value}`}
                className={cx(
                  classes.typeOption,
                  state["redshift_type"] === value && classes.typeSelected,
                )}
                onClick={() => setState({ ...state, redshift_type: value })}
              >
                {label}
              </button>
            ))}
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
              disabled={isSubmitting || invalid || !state["redshift_type"]}
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
                      redshift_type: null,
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
