import { useState } from "react";
import { Link } from "react-router-dom";

import DeleteIcon from "@mui/icons-material/Delete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MuiLink from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { showNotification } from "baselayer/components/Notifications";

import {
  BrokerFilter,
  useAttachFilterToBrokerMutation,
  useGetBrokersQuery,
  useGetFilterCatalogQuery,
} from "../../ducks/brokers";
import { useDeleteGroupFilterMutation } from "../../ducks/filter";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";
import { useAppDispatch } from "../../types/hooks";
import StyledDataGrid from "../StyledDataGrid";
import ConfirmFilterDeletionDialog from "../filter/ConfirmFilterDeletionDialog";

const FilterCatalog = ({ brokerId }: { brokerId?: number }) => {
  const [page, setPage] = useState(0);
  const [numPerPage, setNumPerPage] = useState(25);
  const [name, setName] = useState("");
  const [groupID, setGroupID] = useState<number | "">("");
  const [streamID, setStreamID] = useState<number | "">("");
  const [brokerID, setBrokerID] = useState<number | "" | "none">("");
  const [targets, setTargets] = useState<Record<number, number>>({});
  const [filterToDelete, setFilterToDelete] = useState<{
    id: number;
    name: string;
  } | null>(null);

  const { data, isFetching } = useGetFilterCatalogQuery({
    pageNumber: page + 1,
    numPerPage,
    name: name || undefined,
    groupID,
    streamID,
    brokerID: brokerId ?? brokerID,
  });
  const { data: brokers } = useGetBrokersQuery();
  const { data: groups } = useGetGroupsQuery();
  const { data: streams } = useGetStreamsQuery();
  const [attachFilter] = useAttachFilterToBrokerMutation();
  const [deleteFilter] = useDeleteGroupFilterMutation();
  const dispatch = useAppDispatch();

  const groupList = groups?.userAccessible || [];
  const streamList = (streams as { id: number; name: string }[]) || [];
  const brokerList = brokers || [];
  const brokerName = (id: number) =>
    brokerList.find((b) => b.id === id)?.name ?? `broker ${id}`;
  const groupName = (id: number) =>
    groupList.find((g) => g.id === id)?.name ?? `group ${id}`;
  const streamName = (id: number) =>
    streamList.find((s) => s.id === id)?.name ?? `stream ${id}`;
  const attachable = brokerList.filter(
    (b) => b.active && b.filter_kind !== "none",
  );
  const hasPipeline = (f: { altdata?: Record<string, unknown> }) =>
    Boolean((f.altdata as { boom?: unknown } | undefined)?.boom);

  const onFilterChange =
    <T,>(setter: (v: T) => void) =>
    (v: T) => {
      setter(v);
      setPage(0);
    };

  const handleDeleteFilter = async () => {
    if (!filterToDelete) return;
    try {
      await deleteFilter({ filter_id: filterToDelete.id }).unwrap();
      dispatch(showNotification("Deleted filter"));
    } catch {
      // error notification handled by the base query
    }
    setFilterToDelete(null);
  };

  const columns: any[] = [
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      minWidth: 200,
      renderCell: ({ row: f }: { row: BrokerFilter }) => (
        <>
          {f.broker_id ? (
            <MuiLink
              component={Link}
              to={`/brokers/${f.broker_id}/filter/${f.id}`}
            >
              {f.name}
            </MuiLink>
          ) : (
            f.name
          )}
          {hasPipeline(f) && (
            <Chip
              size="small"
              label="pipeline"
              color="primary"
              sx={{ ml: 1 }}
            />
          )}
        </>
      ),
    },
    {
      field: "group_id",
      headerName: "Group",
      flex: 1,
      minWidth: 140,
      renderCell: ({ row: f }: { row: BrokerFilter }) => (
        <Chip
          size="small"
          label={groupName(f.group_id)}
          component={Link}
          to={`/group/${f.group_id}`}
          clickable
        />
      ),
    },
    {
      field: "stream_id",
      headerName: "Stream",
      flex: 1,
      minWidth: 140,
      valueGetter: (value: number) => streamName(value),
    },
    ...(brokerId
      ? []
      : [
          {
            field: "broker_id",
            headerName: "Broker",
            flex: 1,
            minWidth: 140,
            valueGetter: (value: number | null) =>
              value ? brokerName(value) : "—",
          },
        ]),
    {
      field: "actions",
      headerName: "Actions",
      align: "right",
      headerAlign: "right",
      minWidth: 320,
      renderCell: ({ row: f }: { row: BrokerFilter }) => (
        <Box
          sx={{
            display: "flex",
            gap: 1,
            justifyContent: "flex-end",
            alignItems: "center",
          }}
        >
          {!brokerId && !f.broker_id && (
            <>
              <FormControl size="small" sx={{ minWidth: 180 }}>
                <InputLabel id={`attach-broker-${f.id}`}>Broker</InputLabel>
                <Select
                  labelId={`attach-broker-${f.id}`}
                  label="Broker"
                  value={targets[f.id] ?? ""}
                  onChange={(e) =>
                    setTargets({
                      ...targets,
                      [f.id]: e.target.value as number,
                    })
                  }
                >
                  {attachable.map((b) => (
                    <MenuItem key={b.id} value={b.id}>
                      {b.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                variant="contained"
                size="small"
                disabled={!targets[f.id]}
                onClick={() => {
                  const target = targets[f.id];
                  if (target)
                    attachFilter({
                      filterId: f.id,
                      brokerId: target,
                    });
                }}
              >
                Attach
              </Button>
            </>
          )}
          {f.group_admin && (
            <Tooltip title={`Delete filter "${f.name}"`} placement={"left"}>
              <Button
                color="error"
                onClick={() => setFilterToDelete({ id: f.id, name: f.name })}
              >
                <DeleteIcon />
              </Button>
            </Tooltip>
          )}
        </Box>
      ),
    },
  ];

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          gap: 2,
          mb: 2,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <TextField
          size="small"
          label="Name"
          placeholder="Search"
          value={name}
          onChange={(e) => onFilterChange(setName)(e.target.value)}
        />
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="filter-catalog-group">Group</InputLabel>
          <Select
            labelId="filter-catalog-group"
            label="Group"
            value={groupID}
            onChange={(e) =>
              onFilterChange(setGroupID)(e.target.value as number | "")
            }
          >
            <MenuItem value="">All groups</MenuItem>
            {groupList.map((g) => (
              <MenuItem key={g.id} value={g.id}>
                {g.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="filter-catalog-stream">Stream</InputLabel>
          <Select
            labelId="filter-catalog-stream"
            label="Stream"
            value={streamID}
            onChange={(e) =>
              onFilterChange(setStreamID)(e.target.value as number | "")
            }
          >
            <MenuItem value="">All streams</MenuItem>
            {streamList.map((s) => (
              <MenuItem key={s.id} value={s.id}>
                {s.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        {brokerId ? null : (
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel id="filter-catalog-broker">Broker</InputLabel>
            <Select
              labelId="filter-catalog-broker"
              label="Broker"
              value={brokerID}
              onChange={(e) =>
                onFilterChange(setBrokerID)(
                  e.target.value as number | "" | "none",
                )
              }
            >
              <MenuItem value="">All brokers</MenuItem>
              {brokerList.map((b) => (
                <MenuItem key={b.id} value={b.id}>
                  {b.name}
                </MenuItem>
              ))}
              <MenuItem value="none">No broker</MenuItem>
            </Select>
          </FormControl>
        )}
        <Typography variant="body2" color="text.secondary">
          {`${data?.totalMatches ?? 0} filter${
            (data?.totalMatches ?? 0) === 1 ? "" : "s"
          }`}
        </Typography>
      </Box>

      <StyledDataGrid
        autoHeight
        rows={data?.filters || []}
        columns={columns}
        loading={isFetching}
        localeText={{ noRowsLabel: "No filter matches this search." }}
        disableColumnSorting
        disableColumnMenu
        paginationMode="server"
        rowCount={data?.totalMatches ?? 0}
        paginationModel={{ page, pageSize: numPerPage }}
        onPaginationModelChange={(model: {
          page: number;
          pageSize: number;
        }) => {
          setPage(model.pageSize === numPerPage ? model.page : 0);
          setNumPerPage(model.pageSize);
        }}
      />
      <ConfirmFilterDeletionDialog
        filter={filterToDelete}
        closeDialog={() => setFilterToDelete(null)}
        deleteFunction={handleDeleteFilter}
      />
    </Box>
  );
};

export default FilterCatalog;
