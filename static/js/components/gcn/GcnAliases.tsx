import { useState } from "react";
import Box from "@mui/material/Box";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery } from "../../ducks/profile";
import { useDeleteGcnAliasMutation } from "../../ducks/gcnEvent";
import AddGcnAlias from "./AddGcnAlias";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import RemovableChip from "../RemovableChip";

interface GcnAliasesProps {
  gcnEvent: {
    dateobs?: string;
    aliases: string[];
    [key: string]: any;
  };
  show_title?: boolean;
}

const GcnAliases = ({ gcnEvent, show_title = false }: GcnAliasesProps) => {
  const dispatch = useAppDispatch();
  const [deleteGcnAlias] = useDeleteGcnAliasMutation();
  const { data: userProfile } = useGetProfileQuery();
  const [aliasToDelete, setAliasToDelete] = useState<string | null>(null);

  const permission =
    userProfile?.permissions.includes("System admin") ||
    userProfile?.permissions.includes("Manage GCNs");

  const deleteAlias = () =>
    deleteGcnAlias({
      dateobs: gcnEvent.dateobs as string,
      params: { alias: aliasToDelete },
    })
      .unwrap()
      .then(() => {
        dispatch(showNotification("GCN Event Alias deleted"));
        setAliasToDelete(null);
      })
      .catch(() => {
        // error notification handled by baseQuery
      });

  return (
    <Box sx={{ display: "flex", alignItems: "center" }}>
      {show_title && (
        <Box component="h4" sx={{ m: 0, mr: "0.45rem" }}>
          Aliases:
        </Box>
      )}
      <Box
        sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}
        {...({ name: "gcn_triggers-aliases" } as any)}
      >
        {gcnEvent?.aliases?.map((alias) => (
          <RemovableChip
            key={alias}
            size="small"
            label={alias}
            clickable
            onClick={() =>
              window.open(
                `https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/?event=${
                  alias.split("#")[1] || alias
                }`,
                "_blank",
              )
            }
            {...(permission && { onDelete: () => setAliasToDelete(alias) })}
          />
        ))}
      </Box>
      <AddGcnAlias gcnEvent={gcnEvent} />
      <ConfirmDeletionDialog
        deleteFunction={deleteAlias}
        dialogOpen={aliasToDelete !== null}
        closeDialog={() => setAliasToDelete(null)}
        resourceName="alias"
      />
    </Box>
  );
};

export default GcnAliases;
