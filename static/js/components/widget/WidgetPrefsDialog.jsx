import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import SettingsIcon from "@mui/icons-material/Settings";
import Checkbox from "@mui/material/Checkbox";
import makeStyles from "@mui/styles/makeStyles";
import SaveIcon from "@mui/icons-material/Save";
import TextField from "@mui/material/TextField";
import FormControlLabel from "@mui/material/FormControlLabel";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import Autocomplete from "@mui/material/Autocomplete";
import Button from "../Button";

const useStyles = makeStyles(() => ({
  saveButton: {
    margin: "1rem 0",
  },
  inputSectionDiv: {
    marginBottom: "1rem",
    marginTop: "0.5rem",
  },
  fullWidth: {
    width: "100%",
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
  const groups = useSelector((state) => state.groups.userAccessible);

  const {
    handleSubmit,
    register,
    reset,
    control,

    formState: { errors },
  } = useForm(initialValues);

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
      <Dialog open={open} onClose={handleClose} maxWidth="md">
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(formSubmit)}>
            {Object.keys(initialValues).map((key) => {
              if (
                typeof initialValues[key] === "object" &&
                initialValues[key].constructor === Object
              ) {
                return (
                  <div key={key} className={classes.inputSectionDiv}>
                    <Typography variant="subtitle2">Select {key}:</Typography>
                    {Object.keys(initialValues[key]).map((subKey) =>
                      subKey === "includeCommentsFromBots" ? (
                        <Tooltip
                          key={subKey}
                          title="Bot comments are those posted programmatically using API tokens"
                        >
                          <FormControlLabel
                            control={
                              <Controller
                                render={({ field: { onChange, value } }) => (
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
                        </Tooltip>
                      ) : (
                        <FormControlLabel
                          key={subKey}
                          control={
                            <Controller
                              render={({ field: { onChange, value } }) => (
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
                      ),
                    )}
                  </div>
                );
              }
              if (typeof initialValues[key] === "string") {
                return (
                  <div key={key} className={classes.inputSectionDiv}>
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <TextField
                          data-testid={key}
                          size="small"
                          label={key}
                          inputRef={register(key, { required: true })}
                          name={key}
                          error={!!errors[key]}
                          helperText={errors[key] ? "Required" : ""}
                          variant="outlined"
                          onChange={onChange}
                          value={value}
                          className={classes.fullWidth}
                        />
                      )}
                      name={key}
                      control={control}
                      defaultValue={initialValues[key]}
                    />
                  </div>
                );
              }
              if (typeof initialValues[key] === "boolean") {
                return (
                  <div key={key} className={classes.inputSectionDiv}>
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <FormControlLabel
                          control={
                            <Checkbox
                              onChange={(event) =>
                                onChange(event.target.checked)
                              }
                              checked={value}
                              data-testid={key}
                            />
                          }
                          label={
                            key === "candidatesOnly"
                              ? "Only if source has candidate(s)"
                              : key
                          }
                        />
                      )}
                      name={key}
                      control={control}
                      defaultValue={initialValues[key]}
                    />
                  </div>
                );
              }
              if (key === "groupIds" && Array.isArray(initialValues[key])) {
                return (
                  <div key={key} className={classes.inputSectionDiv}>
                    <Controller
                      name={key}
                      render={({ field: { onChange, value } }) => (
                        <Autocomplete
                          multiple
                          id={key}
                          options={groups || []}
                          getOptionLabel={(group) => group.name}
                          value={(groups || []).filter((group) =>
                            value.includes(group.id),
                          )}
                          onChange={(e, data) =>
                            onChange(data.map((group) => group.id))
                          }
                          filterSelectedOptions
                          renderInput={(params) => (
                            <TextField
                              {...params}
                              error={!!errors[key]}
                              variant="outlined"
                              label="Only show for these groups"
                              size="small"
                            />
                          )}
                          className={classes.fullWidth}
                        />
                      )}
                      control={control}
                      defaultValue={[]}
                    />
                  </div>
                );
              }
              return <div key={key} />;
            })}
            <div className={classes.saveButton}>
              <Button
                secondary
                type="submit"
                name={`${stateBranchName}Submit`}
                endIcon={<SaveIcon />}
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
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.bool,
      PropTypes.arrayOf(PropTypes.string),
      PropTypes.shape({}),
    ]),
  ).isRequired,
  stateBranchName: PropTypes.string.isRequired,
  onSubmit: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
};

export default WidgetPrefsDialog;
