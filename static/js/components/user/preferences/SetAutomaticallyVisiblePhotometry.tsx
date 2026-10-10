import Box from "@mui/material/Box";
import FilterSelect from "./FilterSelect";
import OriginSelect from "./OriginSelect";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";

const SetAutomaticallyVisiblePhotometry = () => {
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
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: 1.5,
        "& > *": { flex: "1 1 14rem" },
      }}
    >
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
    </Box>
  );
};

export default SetAutomaticallyVisiblePhotometry;
