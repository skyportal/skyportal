import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { ReactNode, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { withTheme } from "@rjsf/core";
import validator from "@rjsf/validator-ajv8";

import InputLabel from "@mui/material/InputLabel";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import IconButton from "@mui/material/IconButton";
import ChecklistIcon from "@mui/icons-material/Checklist";
import BugReportIcon from "@mui/icons-material/BugReport";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Chip from "@mui/material/Chip";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Box from "@mui/material/Box";
import InfoIcon from "@mui/icons-material/InfoOutlined";
import FormGroup from "@mui/material/FormGroup";
import FormLabel from "@mui/material/FormLabel";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import SearchableSelect from "../SearchableSelect";
import StyledDataGridBase, { DataGridToolbar } from "../StyledDataGrid";
import TransferList from "../TransferList";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import {
  useGetSharingServicesQuery,
  useAddSharingServiceMutation,
  useEditSharingServiceMutation,
  useDeleteSharingServiceMutation,
  useAddSharingServiceGroupMutation,
  useEditSharingServiceGroupMutation,
  useDeleteSharingServiceGroupMutation,
  useAddSharingServiceGroupAutoPublishersMutation,
  useDeleteSharingServiceGroupAutoPublishersMutation,
  useAddSharingServiceCoauthorMutation,
  useDeleteSharingServiceCoauthorMutation,
  useReorderSharingServiceCoauthorsMutation,
} from "../../ducks/sharingServices";
import { useGetStreamsQuery } from "../../ducks/streams";
import { useGetConfigQuery } from "../../ducks/config";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { CustomCheckboxWidgetMuiTheme } from "../CustomCheckboxWidget";
import { userLabel } from "../../utils/format";
import { useGetUsersQuery } from "../../ducks/users";

const Form = withTheme(CustomCheckboxWidgetMuiTheme as any);

const StyledDataGrid: any = StyledDataGridBase;

const chipListSx = {
  display: "flex",
  alignItems: "center",
  flexWrap: "wrap",
  gap: 0.5,
};

const byName = (a: any, b: any) => a?.name?.localeCompare(b?.name);

const lookupById = (items: any[]): Record<string, any> =>
  Object.fromEntries((items || []).map((item: any) => [item.id, item]));

const renderChips = (labels: string[]) => (
  <Box sx={chipListSx}>
    {labels.map((label) => (
      <Tooltip key={label} title={label} placement="right">
        <Chip size="small" label={label} variant="outlined" />
      </Tooltip>
    ))}
  </Box>
);

interface AddChipProps {
  title: string;
  disabled?: boolean;
  onAdd: () => Promise<void>;
  children: ReactNode;
}

const AddChip = ({ title, disabled, onAdd, children }: AddChipProps) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const add = async () => {
    setLoading(true);
    await onAdd();
    setLoading(false);
    setOpen(false);
  };

  return (
    <>
      <Chip size="small" label="+" onClick={() => setOpen(true)} />
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent
          sx={{ display: "flex", flexDirection: "column", gap: 1, pt: 1 }}
        >
          {children}
          <Box sx={{ display: "flex", justifyContent: "space-between" }}>
            <Button primary onClick={add} disabled={loading || disabled}>
              Add
            </Button>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};

interface SharingServiceGroupProps {
  sharingServiceGroup: any;
  sharingService: any;
  groupsLookup: Record<string, any>;
  usersLookup: Record<string, any>;
}

const SharingServiceGroup = ({
  sharingServiceGroup,
  sharingService,
  groupsLookup,
  usersLookup,
}: SharingServiceGroupProps) => {
  const dispatch = useAppDispatch();
  const [editSharingServiceGroup] = useEditSharingServiceGroupMutation();
  const [addSharingServiceGroupAutoPublishers] =
    useAddSharingServiceGroupAutoPublishersMutation();
  const [deleteSharingServiceGroupAutoPublishers] =
    useDeleteSharingServiceGroupAutoPublishersMutation();
  const [deleteSharingServiceGroup] = useDeleteSharingServiceGroupMutation();
  const [open, setOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [owner, setOwner] = useState(sharingServiceGroup.owner || false);
  const [autoPublishTns, setAutoPublishTns] = useState(
    sharingServiceGroup.auto_share_to_tns,
  );
  const [autoPublishHermes, setAutoPublishHermes] = useState(
    sharingServiceGroup.auto_share_to_hermes,
  );
  const [autoPublishAllowBots, setAutoPublishAllowBots] = useState(
    sharingServiceGroup.auto_sharing_allow_bots || false,
  );
  const [left, setLeft] = useState<any[]>([]);
  const [right, setRight] = useState<any[]>([]);
  const [updating, setUpdating] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const groupName =
    groupsLookup[sharingServiceGroup.group_id]?.name || "loading...";
  const ids = {
    sharing_service_id: sharingServiceGroup.sharing_service_id,
    group_id: sharingServiceGroup.group_id,
  };

  useEffect(() => {
    setOwner(sharingServiceGroup.owner);
    setAutoPublishTns(sharingServiceGroup.auto_share_to_tns);
    setAutoPublishHermes(sharingServiceGroup.auto_share_to_hermes);
    setAutoPublishAllowBots(sharingServiceGroup.auto_sharing_allow_bots);
  }, [sharingServiceGroup]);

  useEffect(() => {
    if (!open) return;
    const isAutoPublisher = (user: any) =>
      sharingServiceGroup.auto_publishers.some(
        (autoPublisher: any) => autoPublisher.user_id === user.id,
      );
    const toOptions = (users: any[]) =>
      users
        .map((user: any) => ({
          id: user.id,
          label: userLabel(user, false, true),
        }))
        .sort((a: any, b: any) => a?.label?.localeCompare(b?.label));

    const groupUsers = Object.values(usersLookup || {}).filter((user: any) =>
      user.groups.some(
        (userGroup: any) => userGroup.id === sharingServiceGroup.group_id,
      ),
    );
    setLeft(
      toOptions(groupUsers.filter((user: any) => !isAutoPublisher(user))),
    );
    setRight(toOptions(groupUsers.filter(isAutoPublisher)));
    setInitialized(true);
  }, [sharingServiceGroup, usersLookup, open]);

  const updateGroup = async () => {
    setUpdating(true);
    const newAutoPublishers = right.map((user: any) => user.id);
    const oldAutoPublishers = sharingServiceGroup.auto_publishers.map(
      (autoPublisher: any) => autoPublisher.user_id,
    );
    const toAdd = newAutoPublishers.filter(
      (id: number) => !oldAutoPublishers.includes(id),
    );
    const toRemove = oldAutoPublishers.filter(
      (id: number) => !newAutoPublishers.includes(id),
    );
    const results = [];
    if (
      owner !== sharingServiceGroup.owner ||
      autoPublishTns !== sharingServiceGroup.auto_share_to_tns ||
      autoPublishHermes !== sharingServiceGroup.auto_share_to_hermes ||
      autoPublishAllowBots !== sharingServiceGroup.auto_sharing_allow_bots
    ) {
      results.push(
        await editSharingServiceGroup({
          ...ids,
          data: {
            owner,
            auto_share_to_tns: autoPublishTns,
            auto_share_to_hermes: autoPublishHermes,
            auto_sharing_allow_bots: autoPublishAllowBots,
          },
        }),
      );
    }
    if (toAdd.length) {
      results.push(
        await addSharingServiceGroupAutoPublishers({ ...ids, user_ids: toAdd }),
      );
    }
    if (toRemove.length) {
      results.push(
        await deleteSharingServiceGroupAutoPublishers({
          ...ids,
          user_ids: toRemove,
        }),
      );
    }
    if (!results.some((result) => "error" in result)) {
      dispatch(showNotification(`Successfully updated group ${groupName}`));
    }
    setUpdating(false);
    setOpen(false);
  };

  const deleteGroup = async () => {
    const result = await deleteSharingServiceGroup(ids);
    if ("error" in result) return;
    dispatch(
      showNotification("Group access to sharing service removed successfully"),
    );
    setOpen(false);
  };

  return (
    <>
      <Tooltip title={groupName} placement="right">
        <Chip
          size="small"
          label={groupName}
          sx={
            sharingServiceGroup.owner
              ? { bgcolor: "#457B9D", color: "white" }
              : undefined
          }
          onClick={() => setOpen(true)}
        />
      </Tooltip>
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="lg">
        <DialogTitle>Set group parameters and auto publishers</DialogTitle>
        <DialogContent>
          <InputLabel>Owner</InputLabel>
          <Switch
            checked={owner}
            onChange={(e) => setOwner(e.target.checked)}
          />
          <FormLabel component="legend">Auto publish to</FormLabel>
          <FormGroup row>
            <Tooltip
              title={
                sharingService.enable_sharing_with_tns
                  ? ""
                  : "TNS publishing is disabled for this sharingService."
              }
            >
              <FormControlLabel
                control={
                  <Checkbox
                    checked={autoPublishTns}
                    onChange={(e) => setAutoPublishTns(e.target.checked)}
                  />
                }
                label="TNS"
                disabled={!sharingService.enable_sharing_with_tns}
              />
            </Tooltip>
            <Tooltip
              title={
                sharingService.enable_sharing_with_hermes
                  ? ""
                  : "Hermes publishing is disabled for this sharingService."
              }
            >
              <FormControlLabel
                control={
                  <Checkbox
                    checked={autoPublishHermes}
                    onChange={(e) => setAutoPublishHermes(e.target.checked)}
                  />
                }
                label="Hermes"
                disabled={!sharingService.enable_sharing_with_hermes}
              />
            </Tooltip>
          </FormGroup>
          {(autoPublishTns || autoPublishHermes) && (
            <>
              <InputLabel>Allow bots to auto publish</InputLabel>
              <Switch
                checked={autoPublishAllowBots}
                onChange={(e) => setAutoPublishAllowBots(e.target.checked)}
              />
            </>
          )}
          {initialized && (
            <Box sx={{ minWidth: "70vw", py: 1 }}>
              <Typography>Auto publishers</Typography>
              <TransferList
                left={left}
                right={right}
                setLeft={setLeft}
                setRight={setRight}
                leftLabel="Group Users"
                rightLabel="AutoPublishers"
              />
            </Box>
          )}
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            <Button primary onClick={updateGroup} disabled={updating}>
              Save
            </Button>
            <Button
              secondary
              onClick={() => setDeleteOpen(true)}
              disabled={updating}
            >
              Delete
            </Button>
            <Button onClick={() => setOpen(false)} disabled={updating}>
              Cancel
            </Button>
          </Box>
        </DialogContent>
        <ConfirmDeletionDialog
          deleteFunction={deleteGroup}
          dialogOpen={deleteOpen}
          closeDialog={() => setDeleteOpen(false)}
          resourceName="sharing service group"
        />
      </Dialog>
    </>
  );
};

interface SharingServiceGroupsProps {
  sharingService: any;
  groupsLookup: Record<string, any>;
  allGroupsLookup: Record<string, any>;
  usersLookup: Record<string, any>;
}

const SharingServiceGroups = ({
  sharingService,
  groupsLookup,
  allGroupsLookup,
  usersLookup,
}: SharingServiceGroupsProps) => {
  const dispatch = useAppDispatch();
  const [addSharingServiceGroup] = useAddSharingServiceGroupMutation();
  const [group, setGroup] = useState<any>(null);
  const [owner, setOwner] = useState(false);

  const sharingServiceGroups = [...(sharingService.groups || [])].sort(
    (a, b) =>
      b.owner - a.owner ||
      (allGroupsLookup[a.group_id]?.name || "").localeCompare(
        allGroupsLookup[b.group_id]?.name || "",
      ),
  );
  const groupOptions = Object.values(groupsLookup)
    .filter(
      (option: any) =>
        !sharingService.groups.some(
          (sharingServiceGroup: any) =>
            sharingServiceGroup.group_id === option.id,
        ),
    )
    .sort(byName);

  const handleAdd = async () => {
    const result = await addSharingServiceGroup({
      sharing_service_id: sharingService.id,
      data: {
        group_id: group,
        owner,
        auto_share_to_tns: false,
        auto_share_to_hermes: false,
        auto_sharing_allow_bots: false,
      },
    });
    if ("error" in result) return;
    setGroup(null);
    setOwner(false);
    dispatch(showNotification("Successfully added group"));
  };

  return (
    <Box sx={chipListSx}>
      {sharingServiceGroups.map((sharingServiceGroup: any) => (
        <SharingServiceGroup
          key={sharingServiceGroup.group_id}
          sharingServiceGroup={sharingServiceGroup}
          sharingService={sharingService}
          groupsLookup={allGroupsLookup}
          usersLookup={usersLookup}
        />
      ))}
      <AddChip title="Add Group" onAdd={handleAdd} disabled={!group}>
        <FormControl sx={{ mt: "0.4rem", minWidth: "20vw" }}>
          <InputLabel>Group</InputLabel>
          <Select
            label="Group"
            value={group || ""}
            onChange={(e) => setGroup(e.target.value)}
          >
            {groupOptions.map((groupOption: any) => (
              <MenuItem key={groupOption.id} value={groupOption.id}>
                {groupOption.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <InputLabel>Owner</InputLabel>
          <Switch
            checked={owner}
            onChange={(e) => setOwner(e.target.checked)}
          />
        </Box>
      </AddChip>
    </Box>
  );
};

interface SharingServiceCoauthorProps {
  sharing_service_id: number;
  user_id: number;
  usersLookup: Record<string, any>;
  position: number;
}

const SharingServiceCoauthor = ({
  sharing_service_id,
  user_id,
  usersLookup,
  position,
}: SharingServiceCoauthorProps) => {
  const dispatch = useAppDispatch();
  const [deleteSharingServiceCoauthor] =
    useDeleteSharingServiceCoauthorMutation();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const label = `${position}. ${userLabel(usersLookup[user_id], false, true)}`;

  const deleteCoauthor = async () => {
    const result = await deleteSharingServiceCoauthor({
      sharing_service_id,
      user_id,
    });
    setDeleteOpen(false);
    if ("error" in result) return;
    dispatch(showNotification("Successfully removed user"));
  };

  return (
    <>
      <Tooltip title={label} placement="right">
        <Chip label={label} size="small" onDelete={() => setDeleteOpen(true)} />
      </Tooltip>
      <ConfirmDeletionDialog
        deleteFunction={deleteCoauthor}
        dialogOpen={deleteOpen}
        closeDialog={() => setDeleteOpen(false)}
        resourceName="coauthor"
      />
    </>
  );
};

interface SharingServiceCoauthorsProps {
  sharingService: any;
  usersLookup: Record<string, any>;
}

const SharingServiceCoauthors = ({
  sharingService,
  usersLookup,
}: SharingServiceCoauthorsProps) => {
  const dispatch = useAppDispatch();
  const [addSharingServiceCoauthor] = useAddSharingServiceCoauthorMutation();
  const [reorderSharingServiceCoauthors] =
    useReorderSharingServiceCoauthorsMutation();
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [userIds, setUserIds] = useState<number[]>([]);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const coauthors = sharingService.coauthors;
  const publishedIds = (coauthors || []).map(
    (coauthor: any) => coauthor.user_id,
  );
  const userOptions = Object.values(usersLookup)
    .filter((user: any) => !publishedIds.includes(user.id))
    .sort((a: any, b: any) =>
      userLabel(a, false, true).localeCompare(userLabel(b, false, true)),
    );

  useEffect(() => {
    setUserIds((coauthors || []).map((coauthor: any) => coauthor.user_id));
  }, [coauthors]);

  const handleAdd = async () => {
    const result = await addSharingServiceCoauthor({
      sharing_service_id: sharingService.id,
      user_id: selectedUser?.id,
    });
    if ("error" in result) return;
    setSelectedUser(null);
    dispatch(showNotification("Successfully added user"));
  };

  const moveTo = (index: number) => {
    if (draggedIndex === null || draggedIndex === index) return;
    const reordered = [...userIds];
    const [moved] = reordered.splice(draggedIndex, 1);
    if (moved === undefined) return;
    reordered.splice(index, 0, moved);
    setUserIds(reordered);
    setDraggedIndex(index);
  };

  const saveOrder = async () => {
    setDraggedIndex(null);
    if (userIds.join() === publishedIds.join()) return;
    const result = await reorderSharingServiceCoauthors({
      sharing_service_id: sharingService.id,
      user_ids: userIds,
    });
    if ("error" in result) {
      setUserIds(publishedIds);
      return;
    }
    dispatch(showNotification("Successfully reordered coauthors"));
  };

  const draggable = userIds.length > 1;

  return (
    <Box data-testid="tour-sharing-service-coauthors" sx={chipListSx}>
      {userIds.map((userId, index) => (
        <Box
          key={userId}
          draggable={draggable}
          onDragStart={(event) => {
            // Firefox only starts a drag once data is set
            event.dataTransfer.setData("text/plain", "");
            setDraggedIndex(index);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            moveTo(index);
          }}
          onDragEnd={saveOrder}
          sx={{ display: "flex", cursor: draggable ? "grab" : "default" }}
        >
          <SharingServiceCoauthor
            sharing_service_id={sharingService.id}
            user_id={userId}
            usersLookup={usersLookup}
            position={index + 1}
          />
        </Box>
      ))}
      <AddChip title="Add Coauthor" onAdd={handleAdd} disabled={!selectedUser}>
        <FormControl sx={{ mt: "0.4rem", minWidth: "20vw" }}>
          <SearchableSelect
            label="Coauthor"
            value={selectedUser}
            onChange={(_event, newValue) => setSelectedUser(newValue)}
            options={userOptions}
            getOptionLabel={(option) => userLabel(option, false, true)}
            isOptionEqualToValue={(option, val) => option?.id === val?.id}
            fullWidth
          />
        </FormControl>
      </AddChip>
      {sharingService.acknowledgments && (
        <Tooltip
          title={`Acknowledgments, added at the end of the author list: "${sharingService.acknowledgments}"`}
          placement="right"
        >
          <Chip
            size="small"
            variant="outlined"
            icon={<InfoIcon />}
            label={sharingService.acknowledgments}
            sx={{ maxWidth: "12rem" }}
          />
        </Tooltip>
      )}
    </Box>
  );
};

const SharingServicesToolbar = ({ onCreate }: { onCreate?: () => void }) => (
  <DataGridToolbar
    title="Sharing Services"
    showColumns={false}
    showQuickFilter={false}
    showExport={false}
  >
    {onCreate && (
      <IconButton onClick={onCreate}>
        <AddIcon />
      </IconButton>
    )}
  </DataGridToolbar>
);

const SharingServicesPage = () => {
  const dispatch = useAppDispatch();
  const { data: currentUser } = useGetProfileQuery();
  const managePermission =
    currentUser?.permissions?.includes("Manage sharing services") ||
    currentUser?.permissions?.includes("System admin");
  const [manageDialogOpen, setManageDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [enablePublishToTNS, setEnablePublishToTNS] = useState(true);
  const [enablePublishToHermes, setEnablePublishToHermes] = useState(true);
  const [sharingServiceToManage, setSharingServiceToManage] = useState<any>({});

  const [addSharingService] = useAddSharingServiceMutation();
  const [editSharingService] = useEditSharingServiceMutation();
  const [deleteSharingServiceMutation] = useDeleteSharingServiceMutation();

  const { data: groupsData } = useGetGroupsQuery();
  const { data: sharingServicesList = [] } = useGetSharingServicesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: streams = [] } = useGetStreamsQuery();
  const allowedInstrumentsForSharing = useGetConfigQuery().data?.[
    "allowedInstrumentsForSharing"
  ] as string[] | undefined;

  // `groups` is frozen RTK Query data, so copy before sorting.
  const groups = [...(groupsData?.userAccessible ?? [])].sort(byName);
  const allowedInstruments = instrumentList.filter((instrument: any) =>
    (allowedInstrumentsForSharing || []).includes(
      instrument.name?.toLowerCase(),
    ),
  );
  const groupsLookup = lookupById(groups);
  const allGroupsLookup = lookupById(groupsData?.all ?? []);
  const usersLookup = lookupById(useGetUsersQuery().data?.users ?? []);

  const submitSharingService = async () => {
    const isEdit = Boolean(sharingServiceToManage?.id);
    const {
      name,
      tns_bot_name,
      owner_group_ids,
      acknowledgments,
      instrument_ids,
      stream_ids,
      testing,
      first_and_last_detections,
      auto_sharing_allow_archival,
      publish_existing_tns_objects,
      tns_bot_id,
      tns_source_group_id,
      tns_api_key,
    } = sharingServiceToManage;

    const data = {
      name,
      tns_bot_name,
      acknowledgments,
      owner_group_ids,
      instrument_ids,
      stream_ids,
      testing,
      photometry_options: {
        first_and_last_detections,
        auto_sharing_allow_archival,
      },
      publish_existing_tns_objects,
      tns_bot_id,
      tns_source_group_id,
      ...((!isEdit || tns_api_key?.length > 0) && {
        _tns_altdata: { api_key: tns_api_key },
      }),
      enable_sharing_with_tns: enablePublishToTNS,
      enable_sharing_with_hermes: enablePublishToHermes,
    };

    const result = isEdit
      ? await editSharingService({ id: sharingServiceToManage.id, data })
      : await addSharingService(data);
    if ("error" in result) return;
    dispatch(
      showNotification(
        `Sharing service ${isEdit ? "edited" : "added"} successfully.`,
      ),
    );
    setManageDialogOpen(false);
    setSharingServiceToManage({});
  };

  const deleteSharingService = async () => {
    const result = await deleteSharingServiceMutation(
      sharingServiceToManage.id,
    );
    if ("error" in result) return;
    dispatch(showNotification("Sharing service deleted successfully."));
    setDeleteDialogOpen(false);
    setSharingServiceToManage({});
  };

  const validate = (errors: any) => {
    const { tns_source_group_id } = sharingServiceToManage;
    if (
      enablePublishToTNS &&
      tns_source_group_id !== "" &&
      Number.isNaN(Number(tns_source_group_id))
    ) {
      errors.tns_source_group_id.addError(
        "TNS reporting group ID must be a number.",
      );
    }
    return errors;
  };

  const getFormSchema = (enableTNS: boolean) => {
    const isCreation = !sharingServiceToManage?.id;
    return {
      type: "object",
      properties: {
        name: { type: "string", title: "Sharing Service Name (unique)" },
        ...(isCreation && {
          owner_group_ids: {
            type: "array",
            title: "Owner Group(s)",
            items: {
              type: "integer",
              enum: groups.map((group: any) => group.id),
            },
            uniqueItems: true,
            default: [],
          },
        }),
        acknowledgments: {
          type: "string",
          title: "Acknowledgments",
          default: "on behalf of ...",
          description:
            "Added at the end of the author list, e.g. 'First Last (Affiliation(s)) ...'",
        },
        instrument_ids: {
          type: "array",
          title: "Instruments to restrict photometry to",
          items: {
            type: "integer",
            enum: allowedInstruments.map((instrument: any) => instrument.id),
          },
          uniqueItems: true,
          default:
            sharingServiceToManage?.instruments?.map((i: any) => i.id) || [],
        },
        ...(streams.length > 0 && {
          stream_ids: {
            type: "array",
            title: "Streams to restrict photometry to (optional)",
            items: {
              type: "integer",
              enum: streams.map((stream: any) => stream.id),
            },
            uniqueItems: true,
            default:
              sharingServiceToManage?.streams?.map((s: any) => s.id) || [],
          },
        }),
        testing: {
          type: "boolean",
          title: "Testing Mode",
          default: true,
          description:
            "If enabled, the sharing service will not publish the data but only store the payload in the DB (useful for debugging).",
        },
        first_and_last_detections: {
          type: "boolean",
          title: "Mandatory first and last detection",
          default: true,
          description:
            "If enabled, the sharing service will only publish objects with both a first and last detection (i.e., at least two detections).",
        },
        ...(enableTNS && {
          tns_bot_name: { type: "string", title: "TNS Bot Name" },
          tns_bot_id: { type: "number", title: "TNS Bot ID" },
          tns_source_group_id: {
            type: "integer",
            title: "TNS Reporting Group ID",
          },
          tns_api_key: { type: "string", title: "TNS API Key" },
          publish_existing_tns_objects: {
            type: "boolean",
            title: "Publish existing TNS objects",
            default: false,
            description:
              "If disabled, skips objects within 2 arcsec already in TNS. If enabled, publish if not yet submitted under this internal name.",
          },
          auto_sharing_allow_archival: {
            type: "boolean",
            title: "Allow TNS archival auto-publishing",
            default: false,
            description:
              "If enabled, the sharing service will submit TNS auto-publish as archival if there is no non-detection prior to the first detection that can be published.",
          },
        }),
      },
      required: [
        "name",
        "acknowledgments",
        "instrument_ids",
        "first_and_last_detections",
        ...(isCreation ? ["owner_group_ids"] : []),
        ...(enableTNS
          ? ["tns_bot_name", "tns_bot_id", "tns_source_group_id"]
          : []),
        ...(isCreation && enableTNS ? ["tns_api_key"] : []),
      ],
    };
  };

  const columns: any[] = [
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      minWidth: 160,
      renderCell: ({ row }: any) => (
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          {row.testing === true && (
            <Tooltip
              title={
                <h2>
                  This sharing service is currently in testing mode. It will not
                  publish any data to TNS but will store the payload in the
                  database instead (useful for debugging purposes). For Hermes,
                  it will publish to the test topic.
                </h2>
              }
              placement="right"
            >
              <BugReportIcon sx={{ color: "orange" }} />
            </Tooltip>
          )}
          <Typography variant="body1">{row.name}</Typography>
        </Box>
      ),
    },
    {
      field: "sending_to",
      headerName: "Sending to",
      flex: 0.7,
      minWidth: 120,
      sortable: false,
      renderCell: ({ row }: any) => (
        <Box sx={chipListSx}>
          {row.enable_sharing_with_tns && (
            <Tooltip
              title={
                <Box sx={{ fontSize: "0.8rem", fontWeight: 500 }}>
                  TNS config:
                  <br />- Bot Name: {row.tns_bot_name}
                  <br />- Bot ID: {row.tns_bot_id}
                  <br />- Reporting Group ID: {row.tns_source_group_id}
                  <br />- Report existing TNS objects:{" "}
                  {row.publish_existing_tns_objects ? "Yes" : "No"}
                </Box>
              }
            >
              <Chip
                size="small"
                label="TNS"
                icon={<InfoIcon />}
                color="primary"
                variant="outlined"
              />
            </Tooltip>
          )}
          {row.enable_sharing_with_hermes && (
            <Chip
              size="small"
              label="Hermes"
              color="primary"
              variant="outlined"
            />
          )}
        </Box>
      ),
    },
    {
      field: "groups",
      headerName: "Groups",
      flex: 1.2,
      minWidth: 170,
      sortable: false,
      renderCell: ({ row }: any) => (
        <SharingServiceGroups
          sharingService={row}
          groupsLookup={groupsLookup}
          allGroupsLookup={allGroupsLookup}
          usersLookup={usersLookup}
        />
      ),
    },
    {
      field: "coauthors",
      headerName: "Coauthors",
      flex: 1.4,
      minWidth: 190,
      sortable: false,
      renderCell: ({ row }: any) => (
        <SharingServiceCoauthors
          sharingService={row}
          usersLookup={usersLookup}
        />
      ),
    },
    {
      field: "instruments",
      headerName: "Instruments",
      flex: 0.7,
      minWidth: 110,
      valueGetter: (_value: any, row: any) =>
        (row.instruments || []).map((i: any) => i.name).join(", "),
      renderCell: ({ row }: any) =>
        renderChips((row.instruments || []).map((i: any) => i.name)),
    },
    {
      field: "streams",
      headerName: "Streams",
      flex: 0.7,
      minWidth: 110,
      valueGetter: (_value: any, row: any) =>
        (row.streams || []).map((stream: any) => stream.name).join(", "),
      renderCell: ({ row }: any) =>
        renderChips((row.streams || []).map((stream: any) => stream.name)),
    },
    {
      field: "manage",
      headerName: "",
      width: managePermission ? 150 : 70,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      resizable: false,
      align: "right",
      renderCell: ({ row }: any) => (
        <Box sx={{ display: "flex", alignItems: "center" }}>
          <Link to={`/sharing_service/${row.id}/submissions`} target="_blank">
            <Tooltip title="View publishing submissions">
              <IconButton>
                <ChecklistIcon />
              </IconButton>
            </Tooltip>
          </Link>
          {managePermission && (
            <>
              <IconButton
                onClick={() => {
                  setSharingServiceToManage(row);
                  setEnablePublishToTNS(row.enable_sharing_with_tns);
                  setEnablePublishToHermes(row.enable_sharing_with_hermes);
                  setManageDialogOpen(true);
                }}
              >
                <EditIcon />
              </IconButton>
              <IconButton
                onClick={() => {
                  setSharingServiceToManage(row);
                  setDeleteDialogOpen(true);
                }}
              >
                <DeleteIcon />
              </IconButton>
            </>
          )}
        </Box>
      ),
    },
  ];

  return (
    <div>
      <StyledDataGrid
        autoHeight
        rows={[...sharingServicesList].sort(byName)}
        columns={columns}
        getRowId={(row: any) => row.id}
        getRowHeight={() => "auto"}
        sx={{ "& .MuiDataGrid-cell": { whiteSpace: "normal", py: 1 } }}
        hideFooter
        initialState={{ pagination: { paginationModel: { pageSize: 100 } } }}
        slots={{ toolbar: SharingServicesToolbar }}
        slotProps={{
          toolbar: {
            onCreate: managePermission
              ? () => {
                  setSharingServiceToManage({});
                  setEnablePublishToTNS(true);
                  setEnablePublishToHermes(true);
                  setManageDialogOpen(true);
                }
              : undefined,
          },
        }}
        showToolbar
      />
      <Dialog
        open={manageDialogOpen}
        onClose={() => {
          setManageDialogOpen(false);
          setSharingServiceToManage({});
        }}
      >
        <DialogTitle>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 1,
            }}
          >
            {sharingServiceToManage.id ? "Edit" : "New"} sharing service
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Tooltip title="Select which services to enable publishing to">
                <InfoIcon
                  fontSize="small"
                  sx={{ cursor: "help", color: "#888" }}
                />
              </Tooltip>
              <Chip
                label="TNS"
                clickable
                onClick={() => setEnablePublishToTNS(!enablePublishToTNS)}
                color={enablePublishToTNS ? "primary" : "default"}
                variant={enablePublishToTNS ? "filled" : "outlined"}
              />
              <Tooltip
                title={
                  <h3>
                    HERMES is a Message Exchange Service for Multi-Messenger
                    Astronomy. Click{" "}
                    <a
                      href="https://hermes.lco.global/about"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      here
                    </a>{" "}
                    for more information.
                  </h3>
                }
              >
                <Chip
                  label="Hermes"
                  clickable
                  onClick={() =>
                    setEnablePublishToHermes(!enablePublishToHermes)
                  }
                  color={enablePublishToHermes ? "primary" : "default"}
                  variant={enablePublishToHermes ? "filled" : "outlined"}
                />
              </Tooltip>
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Form
            formData={sharingServiceToManage}
            onChange={(e: any) => setSharingServiceToManage(e.formData)}
            schema={getFormSchema(enablePublishToTNS) as any}
            uiSchema={{
              owner_group_ids: {
                "ui:enumNames": groups.map((group: any) => group.name),
              },
              instrument_ids: {
                "ui:enumNames": allowedInstruments.map(
                  (instrument: any) => instrument.name,
                ),
              },
              stream_ids: {
                "ui:enumNames": streams.map((stream: any) => stream.name),
              },
            }}
            onSubmit={submitSharingService}
            validator={validator}
            {...({ customValidate: validate } as any)}
          />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteSharingService}
        dialogOpen={deleteDialogOpen}
        closeDialog={() => {
          setDeleteDialogOpen(false);
          setSharingServiceToManage({});
        }}
        resourceName="sharing service"
      />
    </div>
  );
};

export default SharingServicesPage;
