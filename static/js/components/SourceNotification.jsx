import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import { useForm, Controller } from "react-hook-form";

import { useTheme } from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormLabel from "@mui/material/FormLabel";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Select from "@mui/material/Select";
import Input from "@mui/material/Input";
import InputLabel from "@mui/material/InputLabel";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";

import { showNotification } from "baselayer/components/Notifications";
import FormValidationError from "./FormValidationError";
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
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
}));

const getFontStyles = (groupId, groupIds = [], theme) => ({
  fontWeight:
    groupIds.indexOf(groupId) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

const SourceNotification = ({ sourceId }) => {
  const classes = useStyles();
  const groups = useSelector((state) => state.groups.userAccessible);
  const groupIDToName = {};
  groups?.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

  const theme = useTheme();
  const ITEM_HEIGHT = 48;
  const MenuProps = {
    disableScrollLock: true,
    PaperProps: {
      style: {
        maxHeight: ITEM_HEIGHT * 4.5,
        width: 250,
      },
    },
  };

  const [selectedGroups, setSelectedGroups] = useState([]);
  const { handleSubmit, getValues, reset, register, control, errors } =
    useForm();
  const dispatch = useDispatch();

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return formState.groupIds.length !== 0;
  };

  const initialFormState = {
    additionalNotes: "",
    groupIds: [],
    level: "soft",
    sourceId,
  };

  const onSubmit = async () => {
    const formData = {
      ...initialFormState,
      ...getValues(),
    };
    const result = await dispatch(Actions.sendAlert(formData));
    if (result.status === "success") {
      dispatch(showNotification("Notification queued up sucessfully", "info"));
      reset(initialFormState);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        {errors.groupIds && (
          <FormValidationError message="No target group(s) selected for notification" />
        )}
        <div className={classes.formContainer}>
          <FormControl
            className={classes.formControl}
            data-testid="sourceNotification_groupSelect"
          >
            <InputLabel id="notificationGroupSelectLabel">
              Choose Group
            </InputLabel>
            <Controller
              id="groupSelect"
              name="groupIds"
              labelId="notificationGroupSelectLabel"
              as={Select}
              control={control}
              rules={{
                required: true,
                validate: validateGroups,
              }}
              defaultValue={[]}
              onChange={([event]) => {
                setSelectedGroups(event.target.value);
                return event.target.value;
              }}
              input={<Input id="selectGroupsChip" />}
              renderValue={(selected) => (
                <div className={classes.chips}>
                  {selected.map((value) => (
                    <Chip
                      key={value}
                      label={groupIDToName[value]}
                      className={classes.chip}
                    />
                  ))}
                </div>
              )}
              MenuProps={MenuProps}
              multiple
            >
              {groups.length > 0 &&
                groups.map((group) => (
                  <MenuItem
                    value={group.id}
                    key={group.id.toString()}
                    data-testid={`notificationGroupSelect_${group.id}`}
                    style={getFontStyles(group.id, selectedGroups, theme)}
                  >
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
            id="sourcenotification-textarea"
            label="Additional Notes"
            variant="outlined"
            multiline
            defaultValue=""
            name="additionalNotes"
            size="small"
            inputRef={register}
          />
          <Button
            type="submit"
            name="sendNotificationButton"
            variant="contained"
            color="primary"
            data-testid="sendNotificationButton"
          >
            Send Notification
          </Button>
        </div>
      </form>
    </div>
  );
};

SourceNotification.propTypes = {
  sourceId: PropTypes.string.isRequired,
};

export default SourceNotification;
