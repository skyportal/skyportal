import { useEffect } from "react";

import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Checkbox from "@mui/material/Checkbox";
import Typography from "@mui/material/Typography";
import FormControlLabel from "@mui/material/FormControlLabel";

import { Controller, useForm } from "react-hook-form";
import Button from "../Button";

import { useCreateTokenMutation } from "../../ducks/profile";

interface NewTokenFormProps {
  availableAcls?: string[] | undefined;
}

const NewTokenForm = ({ availableAcls }: NewTokenFormProps) => {
  const [createToken] = useCreateTokenMutation();

  const {
    handleSubmit,
    register,
    reset,
    control,
    formState: { errors },
  } = useForm();

  useEffect(() => {
    reset({ acls: Array(availableAcls?.length ?? 0).fill(false) });
  }, [reset, availableAcls]);

  const onSubmit = async (data: any) => {
    try {
      await createToken({
        ...data,
        acls: availableAcls?.filter((_acl, idx) => data.acls[idx]),
      }).unwrap();
      reset();
    } catch {
      // error notification handled by the API layer
    }
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit(onSubmit)}
      sx={{ display: "flex", flexDirection: "column", gap: 2 }}
    >
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-start",
          gap: 1.5,
        }}
      >
        <TextField
          label="Token name"
          size="small"
          {...register("name", { required: true })}
          name="name"
          error={!!errors["name"]}
          helperText={errors["name"] ? "Required" : ""}
          sx={{ flex: "1 1 12rem", maxWidth: "20rem" }}
        />
        <Button primary type="submit" sx={{ height: 40 }}>
          Generate Token
        </Button>
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary">
          Permissions
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(12rem, 1fr))",
            columnGap: 1,
          }}
        >
          {availableAcls?.map((acl, idx) => (
            <FormControlLabel
              key={acl}
              label={<Typography variant="body2">{acl}</Typography>}
              control={
                <Controller
                  name={`acls[${idx}]`}
                  control={control}
                  defaultValue={false}
                  render={({ field: { onChange, value } }) => (
                    <Checkbox
                      size="small"
                      onChange={(event) => onChange(event.target.checked)}
                      checked={value}
                      data-testid={`acls[${idx}]`}
                    />
                  )}
                />
              }
            />
          ))}
        </Box>
      </Box>
    </Box>
  );
};

export default NewTokenForm;
