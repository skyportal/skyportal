import { useForm } from "react-hook-form";
import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";

import Button from "../../Button";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import { useGetConfigQuery } from "../../../ducks/config";

const SpectroscopyButtonsForm = () => {
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const colorPalette = (useGetConfigQuery().data as any)?.colorPalette;
  const { data: profile } = useGetProfileQuery();
  const { spectroscopyButtons } = (profile?.preferences ?? {}) as any;
  const {
    handleSubmit,
    register,
    reset,
    formState: { errors },
  } = useForm();

  const onSubmit = (formValues: any) => {
    const currSpectroscopyButtons = {
      ...(spectroscopyButtons || {}),
      [formValues.spectroscopyButtonName]: {
        color: formValues.spectroscopyColorSelect,
        wavelengths: formValues.spectroscopyButtonWavelengths
          .split(",")
          .map(Number),
      },
    };
    const prefs = {
      spectroscopyButtons: currSpectroscopyButtons,
    };
    updateUserPreferences(prefs);
    reset({
      spectroscopyButtonName: "",
      spectroscopyButtonWavelengths: "",
    });
  };

  const onDelete = (buttonName: string) => {
    const { [buttonName]: _removed, ...currSpectroscopyButtons } =
      spectroscopyButtons || {};
    const prefs = {
      spectroscopyButtons: currSpectroscopyButtons,
    };
    updateUserPreferences(prefs);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {spectroscopyButtons && Object.keys(spectroscopyButtons).length > 0 && (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {Object.entries(spectroscopyButtons).map(
            ([key, value]: [string, any]) => (
              <Chip
                key={key}
                label={key}
                onDelete={() => onDelete(key)}
                color="primary"
                sx={{ backgroundColor: value.color[0] }}
              />
            ),
          )}
        </Box>
      )}
      <Box
        component="form"
        onSubmit={handleSubmit(onSubmit)}
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-start",
          gap: 1.5,
        }}
      >
        <FormControl sx={{ width: "7rem" }}>
          <InputLabel id="spectroscopyColorSelectLabel">Color</InputLabel>
          <Select
            labelId="spectroscopyColorSelectLabel"
            label="Color"
            id="spectroscopyColorSelectInput"
            defaultValue=""
            {...register("spectroscopyColorSelect", { required: true })}
            error={!!errors["spectroscopyColorSelect"]}
          >
            {(colorPalette || []).map((color: any) => (
              <MenuItem key={color} value={color}>
                <Box
                  sx={{
                    width: "1rem",
                    height: "1rem",
                    borderRadius: 0.5,
                    background: color,
                  }}
                />
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          label="Name"
          {...register("spectroscopyButtonName", {
            required: "Name is required",
            validate: (value) =>
              spectroscopyButtons && value in spectroscopyButtons
                ? "A button with this name already exists"
                : true,
          })}
          name="spectroscopyButtonName"
          id="spectroscopyButtonNameInput"
          error={!!errors["spectroscopyButtonName"]}
          helperText={errors["spectroscopyButtonName"]?.message as any}
          sx={{ flex: "1 1 10rem" }}
        />
        <TextField
          label="Wavelengths"
          placeholder="6563, 4861"
          {...register("spectroscopyButtonWavelengths", {
            required: "Wavelengths are required",
          })}
          name="spectroscopyButtonWavelengths"
          id="spectroscopyButtonWavelengthInput"
          error={!!errors["spectroscopyButtonWavelengths"]}
          helperText={
            (errors["spectroscopyButtonWavelengths"]?.message as any) ||
            "Comma separated"
          }
          sx={{ flex: "2 1 12rem" }}
        />
        <Button
          primary
          type="submit"
          id="addSpectroscopyButtonButton"
          aria-label="Add spectral lines"
          sx={{ minWidth: 56, width: 56, height: 56, padding: 0 }}
        >
          <AddIcon />
        </Button>
      </Box>
    </Box>
  );
};

export default SpectroscopyButtonsForm;
