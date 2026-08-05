import { makeStyles } from "tss-react/mui";
import FilterSelect from "./FilterSelect";
import OriginSelect from "./OriginSelect";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";

const useStyles = makeStyles()(() => ({
  form: {
    marginBottom: "1rem",
  },
}));

const SetAutomaticallyVisiblePhotometry = () => {
  const { classes } = useStyles();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const { data: profile } = useGetProfileQuery();
  const { automaticallyVisibleFilters, automaticallyVisibleOrigins } =
    (profile?.preferences ?? {}) as any;
  const onFilterSelectChange = (event: any) => {
    const prefs = {
      automaticallyVisibleFilters: event.target.value.includes(
        "Clear selections",
      )
        ? []
        : event.target.value,
    };
    updateUserPreferences(prefs);
  };
  const onOriginSelectChange = (event: any) => {
    const prefs = {
      automaticallyVisibleOrigins: event.target.value.includes(
        "Clear selections",
      )
        ? []
        : event.target.value,
    };
    updateUserPreferences(prefs);
  };
  const parent = "AutomaticallyVisiblePhotometry";
  return (
    <div>
      <div className={classes.form}>
        <FilterSelect
          onFilterSelectChange={onFilterSelectChange}
          initValue={automaticallyVisibleFilters}
          parent={parent}
        />
        <OriginSelect
          onOriginSelectChange={onOriginSelectChange}
          initValue={automaticallyVisibleOrigins}
          parent={parent}
        />
      </div>
    </div>
  );
};

export default SetAutomaticallyVisiblePhotometry;
