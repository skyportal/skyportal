import { useGetGroupsQuery } from "../../ducks/groups";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { makeStyles } from "tss-react/mui";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormLabel from "@mui/material/FormLabel";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import GroupShareSelect from "../group/GroupShareSelect";
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import { useSendAlertMutation } from "../../ducks/source";

const useStyles = makeStyles()((theme) => ({
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

interface SourceNotificationProps {
  sourceId: string;
}

const SourceNotification = ({ sourceId }: SourceNotificationProps) => {
  const { classes } = useStyles();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const groupIDToName: Record<number, string> = {};
  groups?.forEach((g: any) => {
    groupIDToName[g.id] = g.name;
  });

  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const {
    handleSubmit,
    getValues,
    reset,
    register,
    control,

    formState: { errors },
  } = useForm();
  const dispatch = useAppDispatch();
  const [sendAlert] = useSendAlertMutation();

  const initialFormState = {
    additionalNotes: "",
    groupIds: [] as any[],
    level: "soft",
    sourceId,
  };

  const formSubmit = async () => {
    const formData = {
      ...initialFormState,
      ...getValues(),
    };
    if (selectedGroupIds.length >= 0) {
      formData.groupIds = selectedGroupIds;
    }
    try {
      await sendAlert(formData).unwrap();
      dispatch(showNotification("Notification queued up successfully", "info"));
      reset(initialFormState);
    } catch {
      // error notification handled by the baseQuery
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit(formSubmit)}>
        {errors["groupIds"] && (
          <FormValidationError message="No target group(s) selected for notification" />
        )}
        <div className={classes.formContainer}>
          <FormControl
            className={classes.formControl}
            data-testid="sourceNotification_groupSelect"
          />
          <GroupShareSelect
            groupList={groups}
            setGroupIDs={setSelectedGroupIds}
            groupIDs={selectedGroupIds}
          />
          <FormControl className={classes.formControl}>
            <FormLabel id="levelSelectLabel">Level</FormLabel>
            <Controller
              name="level"
              control={control}
              rules={{ required: true }}
              render={({ field: { onChange, value } }) => (
                <RadioGroup value={value} onChange={onChange}>
                  <FormControlLabel
                    value="soft"
                    control={<Radio />}
                    label="Soft Alert (email)"
                    data-testid="soft"
                  />
                  <FormControlLabel
                    value="hard"
                    control={<Radio />}
                    label="Hard Alert (email + SMS)"
                    data-testid="hard"
                  />
                </RadioGroup>
              )}
            />
          </FormControl>
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                {...register("additionalNotes")}
                id="sourcenotification-textarea"
                label="Additional Notes"
                variant="outlined"
                multiline
                defaultValue=""
                name="additionalNotes"
                size="small"
                error={!!errors["additionalNotes"]}
                helperText={errors["additionalNotes"] ? "Required" : ""}
                onChange={onChange}
                value={value}
              />
            )}
            name="additionalNotes"
            control={control}
          />

          <Button
            primary
            type="submit"
            name="sendNotificationButton"
            data-testid="sendNotificationButton"
            onClick={() => formSubmit()}
          >
            Send Notification
          </Button>
        </div>
      </form>
    </div>
  );
};

export default SourceNotification;
