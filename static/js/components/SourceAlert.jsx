import React from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import { useForm, Controller } from "react-hook-form";

import { makeStyles } from "@material-ui/core/styles";
import FormControl from "@material-ui/core/FormControl";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import FormLabel from "@material-ui/core/FormLabel";
import Radio from "@material-ui/core/Radio";
import RadioGroup from "@material-ui/core/RadioGroup";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import TextField from "@material-ui/core/TextField";
import Button from "@material-ui/core/Button";
import MenuItem from "@material-ui/core/MenuItem";
import Typography from "@material-ui/core/Typography";

import { showNotification } from "baselayer/components/Notifications";
import * as Actions from "../ducks/source";

const useStyles = makeStyles((theme) => ({
  formControl: {
    margin: theme.spacing(1),
    minWidth: 120,
  },
  formContainer: {
    display: "flex",
    flexFlow: "column nowrap",
    "& > div": {
      margin: "0.5rem 0",
    },
  },
}));

const SourceAlert = ({ sourceId }) => {
  const classes = useStyles();
  const groups = useSelector((state) => state.groups.userAccessible);
  const { handleSubmit, getValues, reset, register, control } = useForm();
  const dispatch = useDispatch();
  const initialFormState = {
    additionalNotes: "",
    groupIds: [],
    level: "soft",
    sourceId,
  };

  const onSubmit = () => {
    const formData = {
      ...initialFormState,
      ...getValues(),
    };
    if (formData.groupIds.length === 0) {
      dispatch(
        showNotification("No target group(s) selected for alert", "error")
      );
    } else {
      dispatch(Actions.sendAlert(formData));
      reset(initialFormState);
    }
  };

  return (
    <div>
      <Typography variant="h6">Send an Alert</Typography>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className={classes.formContainer}>
          <FormControl className={classes.formControl}>
            <InputLabel id="alertGroupSelectLabel">Choose Group</InputLabel>
            <Controller
              as={Select}
              name="groupIds"
              control={control}
              rules={{
                required: true,
              }}
              defaultValue={[]}
              multiple
            >
              {groups.length > 0 &&
                groups.map((group) => (
                  <MenuItem value={group.id} key={group.id.toString()}>
                    {group.name}
                  </MenuItem>
                ))}
            </Controller>
          </FormControl>
          <FormControl className={classes.formControl}>
            <FormLabel id="levelSelectLabel">Level</FormLabel>
            <Controller
              as={RadioGroup}
              name="level"
              control={control}
              rules={{ required: true }}
              defaultValue="soft"
            >
              <FormControlLabel
                value="soft"
                control={<Radio />}
                label="Soft Alert (email)"
              />
              <FormControlLabel
                value="hard"
                control={<Radio />}
                label="Hard Alert (email + SMS)"
              />
            </Controller>
          </FormControl>
          <TextField
            id="standard-textarea"
            label="Additional Notes"
            variant="outlined"
            multiline
            defaultValue=""
            name="additionalNotes"
            size="small"
            inputRef={register}
          />
          <Button type="submit" name="alertSubmitButton" variant="contained">
            Send Alert
          </Button>
        </div>
      </form>
    </div>
  );
};

SourceAlert.propTypes = {
  sourceId: PropTypes.string.isRequired,
};

export default SourceAlert;
