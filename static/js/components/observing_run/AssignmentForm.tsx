import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { Controller, useForm } from "react-hook-form";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import TextField from "@mui/material/TextField";
import FormControl from "@mui/material/FormControl";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { useAppSelector } from "../../types/hooks";
import { useSubmitAssignmentMutation } from "../../ducks/source";

import Button from "../Button";

dayjs.extend(utc);

const useStyles = makeStyles()((theme) => ({
  formControl: {
    margin: theme.spacing(1),
    minWidth: 120,
  },
  formContainer: {
    display: "flex",
    flexFlow: "row wrap",
    alignItems: "center",
  },
  observingRunSelectItem: {
    whiteSpace: "break-spaces",
  },
  submitButton: {
    margin: "0.5rem",
  },
}));

export function observingRunTitle(
  observingRun: any,
  instrumentList: any[],
  telescopeList: any[],
  groups: any[],
) {
  const { instrument_id } = observingRun;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];
  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];
  const group = groups?.filter((g) => g.id === observingRun.group_id)[0];

  if (!observingRun?.calendar_date || !instrument?.name || !telescope?.name) {
    return <CircularProgress />;
  }

  let result = `${observingRun?.calendar_date} ${instrument?.name}/${telescope?.nickname}`;

  if (observingRun?.pi || group?.name) {
    result += " (";
    if (observingRun?.pi) {
      result += `PI: ${observingRun.pi}`;
    }
    if (group?.name) {
      result += ` / Group: ${group?.name}`;
    }
    result += ")";
  }

  return result;
}

interface AssignmentFormProps {
  obj_id: string;
  observingRunList: any[];
}

const AssignmentForm = ({ obj_id, observingRunList }: AssignmentFormProps) => {
  const [submitAssignment] = useSubmitAssignmentMutation();
  const { classes } = useStyles();

  const { instrumentList } = useAppSelector((state) => state["instruments"]);
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const groups = useGetGroupsQuery().data?.all ?? [];

  const { handleSubmit, getValues, reset, register, control } = useForm();

  // the use of integer dates leads to some upcoming runs being
  // left out depending on the timezone
  const upcomingObservingRuns = observingRunList.filter((run: any) =>
    dayjs().isBefore(dayjs(run.run_end_utc).add(2, "day")),
  );

  if (upcomingObservingRuns.length === 0) {
    return (
      <Typography variant="subtitle2">
        No upcoming observing runs to assign target to...
      </Typography>
    );
  }

  const initialFormState = {
    comment: "",
    run_id:
      upcomingObservingRuns.length > 0 ? upcomingObservingRuns[0].id : null,
    priority: "1",
    obj_id,
  };

  const onSubmit = () => {
    const formData = {
      // Need to add obj_id, etc to form data for request
      ...initialFormState,
      ...getValues(),
    };
    submitAssignment(formData);
    reset(initialFormState);
  };

  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className={classes.formContainer}>
          <FormControl className={classes.formControl}>
            <InputLabel id="assignmentSelectLabel">Choose Run</InputLabel>
            <Controller
              {...({
                inputProps: { MenuProps: { disableScrollLock: true } },
                labelId: "assignmentSelect",
                "data-testid": "assignmentSelect",
              } as any)}
              name="run_id"
              control={control}
              rules={{ required: true }}
              defaultValue={
                upcomingObservingRuns.length > 0
                  ? upcomingObservingRuns[0].id
                  : null
              }
              render={({ field: { onChange, value } }) => (
                <Select
                  labelId="assignmentSelect"
                  onChange={onChange}
                  value={value}
                  size="small"
                >
                  {upcomingObservingRuns?.map((observingRun: any) => (
                    <MenuItem
                      value={observingRun.id}
                      key={observingRun.id.toString()}
                      className={classes.observingRunSelectItem}
                    >
                      {observingRunTitle(
                        observingRun,
                        instrumentList,
                        telescopeList,
                        groups,
                      )}
                    </MenuItem>
                  ))}
                </Select>
              )}
            />
          </FormControl>
          <FormControl className={classes.formControl}>
            <InputLabel id="prioritySelectLabel">Priority</InputLabel>
            <Controller
              {...({
                inputProps: { MenuProps: { disableScrollLock: true } },
                labelId: "prioritySelect",
              } as any)}
              defaultValue="1"
              name="priority"
              control={control}
              rules={{ required: true }}
              render={({ field: { onChange, value } }) => (
                <Select
                  labelId="prioritySelect"
                  onChange={onChange}
                  value={value}
                  size="small"
                >
                  {["1", "2", "3", "4", "5"].map((prio) => (
                    <MenuItem value={prio} key={prio}>
                      {prio}
                    </MenuItem>
                  ))}
                </Select>
              )}
            />
          </FormControl>
          <div className={classes.formControl}>
            <TextField
              {...register("comment")}
              id="standard-textarea"
              label="Comment"
              variant="outlined"
              multiline
              defaultValue=""
              name="comment"
              data-testid="assignmentCommentInput"
              size="small"
            />
          </div>
          <Button
            primary
            type="submit"
            name="assignmentSubmitButton"
            data-testid="assignmentSubmitButton"
            className={classes.submitButton}
          >
            Submit
          </Button>
        </div>
      </form>
    </div>
  );
};

export default AssignmentForm;
