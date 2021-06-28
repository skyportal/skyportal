import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import { useForm, Controller } from "react-hook-form";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import SettingsIcon from "@material-ui/icons/Settings";
import Button from "@material-ui/core/Button";
import Checkbox from "@material-ui/core/Checkbox";
import { makeStyles } from "@material-ui/core/styles";
import SaveIcon from "@material-ui/icons/Save";
import TextField from "@material-ui/core/TextField";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Typography from "@material-ui/core/Typography";

const useStyles = makeStyles(() => ({
  saveButton: {
    margin: "1rem 0",
  },
  inputSectionDiv: {
    marginBottom: "1rem",
  },
}));

const WidgetPrefsDialog = ({
  title,
  initialValues,
  onSubmit,
  stateBranchName,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);

  const { handleSubmit, register, errors, reset, control } =
    useForm(initialValues);

  useEffect(() => {
    reset(initialValues);
  }, [initialValues, reset]);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const formSubmit = (formData) => {
    const payload = { [stateBranchName]: formData };
    dispatch(onSubmit(payload));
    setOpen(false);
  };

  return (
    <div>
      <SettingsIcon
        id={`${stateBranchName}SettingsIcon`}
        fontSize="small"
        onClick={handleClickOpen}
      />
      <Dialog open={open} onClose={handleClose} style={{ position: "fixed" }}>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          <form
            noValidate
            autoComplete="off"
            onSubmit={handleSubmit(formSubmit)}
          >
            {Object.keys(initialValues).map((key) => {
              if (
                typeof initialValues[key] === "object" &&
                initialValues[key].constructor === Object
              ) {
                return (
                  <div key={key} className={classes.inputSectionDiv}>
                    <Typography variant="subtitle2">Select {key}:</Typography>
                    {Object.keys(initialValues[key]).map((subKey) => (
                      <FormControlLabel
                        key={subKey}
                        control={
                          <Controller
                            render={({ onChange, value }) => (
                              <Checkbox
                                onChange={(event) =>
                                  onChange(event.target.checked)
                                }
                                checked={value}
                                data-testid={`${key}.${subKey}`}
                              />
                            )}
                            name={`${key}.${subKey}`}
                            control={control}
                            defaultValue={false}
                          />
                        }
                        label={subKey}
                      />
                    ))}
                  </div>
                );
              }
              if (typeof initialValues[key] === "string") {
                return (
                  <div key={key} className={classes.inputSectionDiv}>
                    <TextField
                      data-testid={key}
                      size="small"
                      label={key}
                      inputRef={register({ required: true })}
                      name={key}
                      error={!!errors[key]}
                      helperText={errors[key] ? "Required" : ""}
                      variant="outlined"
                    />
                  </div>
                );
              }
              return <div key={key} />;
            })}
            <div className={classes.saveButton}>
              <Button
                color="primary"
                variant="contained"
                type="submit"
                startIcon={<SaveIcon />}
              >
                Save
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

WidgetPrefsDialog.propTypes = {
  initialValues: PropTypes.objectOf(
    PropTypes.oneOfType([PropTypes.string, PropTypes.shape({})])
  ).isRequired,
  stateBranchName: PropTypes.string.isRequired,
  onSubmit: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
};

export default WidgetPrefsDialog;
