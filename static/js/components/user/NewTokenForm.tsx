import { useEffect } from "react";

import TextField from "@mui/material/TextField";
import Checkbox from "@mui/material/Checkbox";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import FormControlLabel from "@mui/material/FormControlLabel";

/* For group selection:
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
*/
import { Controller, useForm } from "react-hook-form";
import Button from "../Button";

import { useCreateTokenMutation } from "../../ducks/profile";

interface NewTokenFormProps {
  availableAcls: string[];
}

// const NewTokenForm = ({ acls, groups }) => {
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
    reset({
      acls: Array(availableAcls?.length ?? 0).fill(false),
    });
  }, [reset, availableAcls]);

  const onSubmit = async (data: any) => {
    const selectedACLs = availableAcls?.filter(
      (_include, idx) => data.acls[idx],
    );
    data.acls = selectedACLs;

    // Token groups are not currently supported
    /*
    if (data.group === 'All') {
      delete data.group;
    }
    */

    try {
      await createToken(data).unwrap();
      reset();
    } catch {
      // error notification handled by the API layer
    }
  };

  return (
    <div>
      <Typography variant="h5">
        Generate New Token for Command-Line Authentication
      </Typography>
      <Card>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            <Box>
              <TextField
                label="Token name"
                {...register("name", { required: true })}
                name="name"
                error={!!errors["name"]}
                helperText={errors["name"] ? "Required" : ""}
              />
            </Box>
            <Box>
              <Box
                component="span"
                sx={{
                  mr: 1,
                  fontWeight: "bold",
                }}
              >
                ACLs:
              </Box>
              {availableAcls?.map((acl, idx) => (
                <FormControlLabel
                  key={acl}
                  control={
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <Checkbox
                          onChange={(event) => onChange(event.target.checked)}
                          checked={value}
                          data-testid={`acls[${idx}]`}
                        />
                      )}
                      name={`acls[${idx}]`}
                      control={control}
                      defaultValue={false}
                    />
                  }
                  label={acl}
                />
              ))}
            </Box>
            {/*
            For when we start to support group selection
            Select Token Group:
            <Controller
              as={(
                <Select>
                  <MenuItem value="All" key="0">
                    All
                  </MenuItem>
                  {groups.map((group) => (
                    <MenuItem value={group.id} key={group.id}>
                      {group.name}
                    </MenuItem>
                  ))}
                </Select>
              )}
              name="group"
              control={control}
              defaultValue="All"
            /> */}
            <Button secondary type="submit">
              Generate Token
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default NewTokenForm;
