import { useEffect } from "react";

import TextField from "@mui/material/TextField";
import Checkbox from "@mui/material/Checkbox";
import Typography from "@mui/material/Typography";
import FormControlLabel from "@mui/material/FormControlLabel";

import { Controller, useForm } from "react-hook-form";
import Button from "../Button";
import Paper from "../Paper";

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
    <Paper data-testid="tour-profile-token">
      <Typography variant="h6" sx={{ mb: 1 }}>
        Generate New Token for Command-Line Authentication
      </Typography>
      <form
        onSubmit={handleSubmit(onSubmit)}
        style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
      >
        <TextField
          label="Token name"
          {...register("name", { required: true })}
          name="name"
          error={!!errors["name"]}
          helperText={errors["name"] ? "Required" : ""}
          sx={{ maxWidth: "20rem" }}
        />
        <div>
          <b>ACLs: </b>
          {availableAcls?.map((acl, idx) => (
            <FormControlLabel
              key={acl}
              label={acl}
              control={
                <Controller
                  name={`acls[${idx}]`}
                  control={control}
                  defaultValue={false}
                  render={({ field: { onChange, value } }) => (
                    <Checkbox
                      onChange={(event) => onChange(event.target.checked)}
                      checked={value}
                      data-testid={`acls[${idx}]`}
                    />
                  )}
                />
              }
            />
          ))}
        </div>
        <Button secondary type="submit" sx={{ alignSelf: "flex-start" }}>
          Generate Token
        </Button>
      </form>
    </Paper>
  );
};

export default NewTokenForm;
