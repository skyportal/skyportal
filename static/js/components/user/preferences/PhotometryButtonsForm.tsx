import { useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import { useForm } from "react-hook-form";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Button from "../../Button";
import FilterSelect from "./FilterSelect";
import OriginSelect from "./OriginSelect";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import DeletableChips from "../../DeletableChips";

const PhotometryButtonsForm = () => {
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const { data: profile } = useGetProfileQuery();
  const { photometryButtons } = (profile?.preferences ?? {}) as any;
  const {
    handleSubmit,
    register,
    control,
    reset,

    formState: { errors },
  } = useForm();
  const [selectedFilters, setSelectedFilters] = useState<any[]>([]);
  const [selectedOrigins, setSelectedOrigins] = useState<any[]>([]);

  const onFilterSelectChange = (event: any) => {
    setSelectedFilters(
      event.target.value.includes("Clear selections") ? [] : event.target.value,
    );
  };
  const onOriginSelectChange = (event: any) => {
    setSelectedOrigins(
      event.target.value.includes("Clear selections") ? [] : event.target.value,
    );
  };

  const onSubmit = (formValues: any) => {
    const currPhotButtons = {
      ...(photometryButtons || {}),
      [formValues.photometryButtonName]: {
        filters: selectedFilters,
        origins: selectedOrigins,
      },
    };
    const prefs = {
      photometryButtons: currPhotButtons,
    };
    updateUserPreferences(prefs);
    setSelectedFilters([]);
    setSelectedOrigins([]);
    reset({
      photometryButtonName: "",
    });
  };

  const onDelete = (buttonName: string) => {
    const { [buttonName]: _removed, ...currPhotButtons } =
      photometryButtons || {};
    const prefs = {
      photometryButtons: currPhotButtons,
    };
    updateUserPreferences(prefs);
  };

  const parent = "PhotometryButtonsForm";

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {photometryButtons && Object.keys(photometryButtons).length > 0 && (
        <DeletableChips
          items={Object.keys(photometryButtons)}
          onDelete={onDelete}
        />
      )}
      <Box
        component="form"
        onSubmit={handleSubmit(onSubmit)}
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-start",
          gap: 1.5,
          "& > .MuiFormControl-root": {
            flex: "1 1 9rem",
            minWidth: 0,
            width: "auto",
          },
        }}
      >
        <FilterSelect
          initValue={selectedFilters}
          onFilterSelectChange={onFilterSelectChange}
          parent={parent}
          {...({ control } as any)}
        />
        <OriginSelect
          initValue={selectedOrigins}
          onOriginSelectChange={onOriginSelectChange}
          parent={parent}
          {...({ control } as any)}
        />
        <TextField
          label="Name"
          {...register("photometryButtonName", {
            required: true,
            validate: (value) => {
              if (photometryButtons) {
                return !(value in photometryButtons);
              }
              return true;
            },
          })}
          name="photometryButtonName"
          id="photometryButtonNameInput"
          error={!!errors["photometryButtonName"]}
          helperText={
            errors["photometryButtonName"]
              ? "Required, and not used by another button"
              : ""
          }
        />
        <Button
          primary
          type="submit"
          id="addPhotometryButtonButton"
          aria-label="Add photometry button"
          sx={{ minWidth: 56, width: 56, height: 56, padding: 0 }}
        >
          <AddIcon />
        </Button>
      </Box>
    </Box>
  );
};

export default PhotometryButtonsForm;
