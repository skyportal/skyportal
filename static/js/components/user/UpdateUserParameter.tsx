import React, { useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import SaveIcon from "@mui/icons-material/Save";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import { usePatchUserMutation } from "../../ducks/users";

interface UpdateUserParameterProps {
  user: {
    id: number;
    username?: string;
    [key: string]: any;
  };
  parameter: string | string[];
}

const humanize = (parameter: string) =>
  parameter.replace(/_/g, " ").replace(/^./, (letter) => letter.toUpperCase());

const UpdateUserParameter = ({ user, parameter }: UpdateUserParameterProps) => {
  const dispatch = useAppDispatch();
  const [patchUser, { isLoading }] = usePatchUserMutation();
  const parameters = Array.isArray(parameter) ? parameter : [parameter];

  const [values, setValues] = useState<Record<string, any>>({});
  const [dialogOpen, setDialogOpen] = useState(false);

  const openDialog = () => {
    setValues(
      Object.fromEntries(parameters.map((name) => [name, user[name] ?? ""])),
    );
    setDialogOpen(true);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues({ ...values, [e.target.name]: e.target.value });

  const handleSubmit = async () => {
    try {
      await patchUser({ id: user.id, data: values }).unwrap();
      dispatch(showNotification("User successfully updated."));
      setDialogOpen(false);
    } catch {
      // error notification handled by the base query
    }
  };

  return (
    <>
      <EditIcon
        fontSize="small"
        sx={{ height: "0.75rem", cursor: "pointer" }}
        onClick={openDialog}
      />
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Update Name</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
            {parameters.map((name) => (
              <TextField
                key={name}
                size="small"
                label={humanize(name)}
                name={name}
                value={values[name] ?? ""}
                onChange={handleChange}
                variant="outlined"
              />
            ))}
            <Box>
              <Button
                secondary
                onClick={handleSubmit}
                endIcon={<SaveIcon />}
                size="large"
                disabled={isLoading}
              >
                Save
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UpdateUserParameter;
