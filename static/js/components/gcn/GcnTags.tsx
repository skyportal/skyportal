import { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery } from "../../ducks/profile";
import { useDeleteGcnTagMutation } from "../../ducks/gcnTags";
import { useGetConfigQuery } from "../../ducks/config";
import AddGcnTag from "./AddGcnTag";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import RemovableChip from "../RemovableChip";

const aliasId = (aliases: string[] | undefined, prefix: string) =>
  aliases?.find((alias) => alias.startsWith(`${prefix}#`))?.split("#")[1];

interface GcnTagsProps {
  gcnEvent: {
    dateobs: string;
    tags?: string[];
    aliases?: string[];
    localizations?: { id?: number; localization_name?: string; tags?: any[] }[];
    [key: string]: any;
  };
  addTags?: boolean;
}

const GcnTags = ({ gcnEvent, addTags = true }: GcnTagsProps) => {
  const dispatch = useAppDispatch();
  const [deleteGcnTag] = useDeleteGcnTagMutation();
  const { data: userProfile } = useGetProfileQuery();
  const tagColors = (useGetConfigQuery().data as any)?.gcnTagsClasses ?? {};
  const [tagToDelete, setTagToDelete] = useState<string | null>(null);

  const permission =
    userProfile?.permissions.includes("System admin") ||
    userProfile?.permissions.includes("Manage GCNs");

  const graceid = aliasId(gcnEvent.aliases, "LVC");
  const fermiid = aliasId(gcnEvent.aliases, "FERMI");
  const links: Record<string, string | undefined> = {
    LVC: graceid && `https://gracedb.ligo.org/superevents/${graceid}/view/`,
    Fermi:
      fermiid &&
      `http://heasarc.gsfc.nasa.gov/FTP/fermi/data/gbm/triggers/${gcnEvent.dateobs.slice(0, 4)}/${fermiid}/quicklook/`,
  };
  const localizationTags = [
    ...new Set(
      gcnEvent.localizations?.flatMap(
        (loc) => loc.tags?.map((tag: any) => tag.text) ?? [],
      ),
    ),
  ];

  const deleteTag = () =>
    deleteGcnTag({ gcnEventID: gcnEvent.dateobs, tag: tagToDelete! })
      .unwrap()
      .then(() => {
        dispatch(showNotification("GCN Event Tag deleted"));
        setTagToDelete(null);
      })
      .catch(() => {
        // error notification handled centrally by the base query
      });

  return (
    <Box
      sx={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 0.5 }}
      {...({ name: "gcn_triggers-tags" } as any)}
    >
      {[...new Set(gcnEvent.tags ?? [])].map((tag) => (
        <RemovableChip
          key={tag}
          size="small"
          label={tag}
          {...(links[tag]
            ? {
                component: "a",
                href: links[tag],
                target: "_blank",
                clickable: true,
              }
            : { sx: { backgroundColor: tagColors[tag] } })}
          {...(permission && {
            onDelete: (event: any) => {
              event.preventDefault();
              setTagToDelete(tag);
            },
          })}
        />
      ))}
      {localizationTags.map((tag) => (
        <Chip
          key={tag}
          size="small"
          variant="outlined"
          label={tag}
          sx={{ borderColor: tagColors[tag] }}
        />
      ))}
      {addTags && permission && <AddGcnTag gcnEvent={gcnEvent as any} />}
      <ConfirmDeletionDialog
        deleteFunction={deleteTag}
        dialogOpen={tagToDelete !== null}
        closeDialog={() => setTagToDelete(null)}
        resourceName="tag"
      />
    </Box>
  );
};

export default GcnTags;
