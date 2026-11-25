import { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import { useUpdateSourceMutation } from "../../ducks/source";
import EditDialog, { emptyChipSx } from "./EditDialog";

interface SourceAliasProps {
  source: {
    id: string;
    alias?: string[] | null;
  };
  readOnly?: boolean;
}

const SourceAlias = ({ source, readOnly = false }: SourceAliasProps) => {
  const dispatch = useAppDispatch();
  const [updateSource] = useUpdateSourceMutation();
  const [open, setOpen] = useState(false);
  const [alias, setAlias] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const aliases = source.alias ?? [];
  const newAlias = alias.trim();
  const duplicate = aliases.includes(newAlias);
  const invalid = isSubmitting || !newAlias || duplicate;

  const save = async (aliasList: string[], message: string) => {
    setIsSubmitting(true);
    const result = await updateSource({
      id: source.id,
      payload: { alias: aliasList },
    });
    setIsSubmitting(false);
    if ("error" in result) return false;
    dispatch(showNotification(message));
    return true;
  };

  const add = async () => {
    if (
      await save([...aliases, newAlias], "Source alias successfully updated.")
    ) {
      setOpen(false);
    }
  };

  return (
    <>
      <Tooltip title={aliases.length > 1 ? aliases.join(", ") : ""}>
        <Chip
          size="small"
          data-testid="aliasChip"
          variant={aliases.length ? "filled" : "outlined"}
          sx={aliases.length ? undefined : emptyChipSx}
          label={
            aliases.length
              ? `${aliases[0]}${aliases.length > 1 ? ` +${aliases.length - 1}` : ""}`
              : "None"
          }
          {...(readOnly
            ? {}
            : {
                onClick: () => {
                  setAlias("");
                  setOpen(true);
                },
              })}
        />
      </Tooltip>
      <EditDialog
        open={open}
        onClose={() => setOpen(false)}
        title="Aliases"
        description="Other names this source is known by"
        actions={
          <Button
            primary
            onClick={add}
            disabled={invalid}
            data-testid="addAliasSubmitButton"
          >
            Add
          </Button>
        }
      >
        {aliases.length > 0 && (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
            {aliases.map((a) => (
              <Chip
                key={a}
                label={a}
                size="small"
                disabled={isSubmitting}
                onDelete={() =>
                  save(
                    aliases.filter((other) => other !== a),
                    "Source alias removed successfully.",
                  )
                }
              />
            ))}
          </Box>
        )}
        <TextField
          data-testid="addAliasTextfield"
          size="small"
          label="New alias"
          value={alias}
          onChange={(e) => setAlias(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !invalid) add();
          }}
          error={duplicate}
          helperText={duplicate ? "Already an alias of this source" : ""}
          autoFocus
          fullWidth
        />
      </EditDialog>
    </>
  );
};

export default SourceAlias;
