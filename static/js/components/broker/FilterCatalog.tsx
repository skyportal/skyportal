import { useState } from "react";
import { Link } from "react-router-dom";

import CheckIcon from "@mui/icons-material/Check";
import DeleteIcon from "@mui/icons-material/Delete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import MuiLink from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { GridSortModel } from "@mui/x-data-grid";
import { showNotification } from "baselayer/components/Notifications";

import {
  BrokerFilter,
  FilterCatalogQuery,
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
  const [query, setQuery] = useState<FilterCatalogQuery>({
    name: "",
    groupID: "",
    streamID: "",
    brokerID: "",
  });
  const [sortModel, setSortModel] = useState<GridSortModel>([]);
  const [targets, setTargets] = useState<Record<number, number>>({});
  const [filterToDelete, setFilterToDelete] = useState<BrokerFilter | null>(
    null,
  );

  const { data, isFetching } = useGetFilterCatalogQuery({
    ...query,
    pageNumber: page + 1,
    numPerPage,
    name: query.name || undefined,
    brokerID: brokerId ?? query.brokerID,
    ...(sortModel[0]?.sort && {
      sortBy: "active",
      sortOrder: sortModel[0].sort,
    }),
  });
  const { data: brokers = [] } = useGetBrokersQuery();
  const { data: groups } = useGetGroupsQuery();
  const { data: streams } = useGetStreamsQuery();
  const [attachFilter] = useAttachFilterToBrokerMutation();
  const [deleteFilter] = useDeleteGroupFilterMutation();
  const dispatch = useAppDispatch();

  const groupList = groups?.userAccessible || [];
  const streamList = (streams as { id: number; name: string }[]) || [];
  const total = data?.totalMatches ?? 0;
  const brokerName = (id: number) =>
    brokers.find((b) => b.id === id)?.name ?? `broker ${id}`;

  const updateQuery = (patch: FilterCatalogQuery) => {
    setQuery({ ...query, ...patch });
    setPage(0);
  };

  const handleDeleteFilter = async () => {
    const res = await deleteFilter({ filter_id: filterToDelete!.id });
    if ("data" in res) dispatch(showNotification("Deleted filter"));
    setFilterToDelete(null);
  };

  const columns: any[] = [
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      minWidth: 200,
      sortable: false,
      renderCell: ({ row: f }: { row: BrokerFilter }) => (
        <>
          <MuiLink component={Link} to={`/filter/${f.id}`}>
            {f.name}
          </MuiLink>
          {Boolean(f.altdata?.["boom"]) && (
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
      sortable: false,
      renderCell: ({ row: f }: { row: BrokerFilter }) => (
        <Chip
          size="small"
          label={
            groupList.find((g) => g.id === f.group_id)?.name ??
            `group ${f.group_id}`
          }
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
      sortable: false,
      valueGetter: (value: number) =>
        streamList.find((s) => s.id === value)?.name ?? `stream ${value}`,
    },
    ...(brokerId
      ? []
      : [
          {
            field: "broker_id",
            headerName: "Broker",
            flex: 1,
            minWidth: 290,
            sortable: false,
            renderCell: ({ row: f }: { row: BrokerFilter }) =>
              f.broker_id ? (
                brokerName(f.broker_id)
              ) : (
                <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                  <Select
                    size="small"
                    displayEmpty
                    value={targets[f.id] ?? ""}
                    renderValue={(value) =>
                      value ? (
                        brokerName(value)
                      ) : (
                        <Box component="span" sx={{ color: "text.secondary" }}>
                          Attach broker
                        </Box>
                      )
                    }
                    onKeyDown={(e) => e.stopPropagation()}
                    onChange={(e) =>
                      setTargets({ ...targets, [f.id]: Number(e.target.value) })
                    }
                    sx={{ minWidth: 180 }}
                  >
                    {brokers
                      .filter((b) => b.active && b.filter_kind !== "none")
                      .map((b) => (
                        <MenuItem key={b.id} value={b.id}>
                          {b.name}
                        </MenuItem>
                      ))}
                  </Select>
                  <IconButton
                    aria-label="Attach"
                    color="success"
                    disabled={!targets[f.id]}
                    onClick={() =>
                      attachFilter({ filterId: f.id, brokerId: targets[f.id]! })
                    }
                  >
                    <CheckIcon />
                  </IconButton>
                </Box>
              ),
          },
        ]),
    {
      field: "active",
      headerName: "Active",
      width: 110,
      sortingOrder: ["desc", "asc", null],
      renderCell: ({ row: f }: { row: BrokerFilter }) =>
        f.active != null && (
          <Chip
            size="small"
            label={f.active ? "active" : "inactive"}
            color={f.active ? "success" : "default"}
          />
        ),
    },
    {
      field: "actions",
      headerName: "Actions",
      align: "right",
      headerAlign: "right",
      width: 100,
      sortable: false,
      renderCell: ({ row: f }: { row: BrokerFilter }) =>
        f.group_admin && (
          <Tooltip title={`Delete filter "${f.name}"`} placement="left">
            <Button color="error" onClick={() => setFilterToDelete(f)}>
              <DeleteIcon />
            </Button>
          </Tooltip>
        ),
    },
  ];

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}
    >
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
          value={query.name}
          onChange={(e) => updateQuery({ name: e.target.value })}
        />
        {[
          { key: "groupID" as const, label: "Group", options: groupList },
          { key: "streamID" as const, label: "Stream", options: streamList },
          ...(brokerId
            ? []
            : [
                { key: "brokerID" as const, label: "Broker", options: brokers },
              ]),
        ].map(({ key, label, options }) => (
          <TextField
            key={key}
            select
            size="small"
            label={label}
            value={query[key]}
            onChange={(e) =>
              updateQuery({ [key]: e.target.value } as FilterCatalogQuery)
            }
            sx={{ minWidth: 160 }}
          >
            <MenuItem value="">{`All ${label.toLowerCase()}s`}</MenuItem>
            {options.map((o) => (
              <MenuItem key={o.id} value={o.id}>
                {o.name}
              </MenuItem>
            ))}
            {key === "brokerID" && <MenuItem value="none">No broker</MenuItem>}
          </TextField>
        ))}
        <Typography variant="body2" color="text.secondary">
          {`${total} filter${total === 1 ? "" : "s"}`}
        </Typography>
      </Box>

      <StyledDataGrid
        rows={data?.filters || []}
        columns={columns}
        loading={isFetching}
        localeText={{ noRowsLabel: "No filter matches this search." }}
        disableColumnMenu
        sx={{ flex: 1, minHeight: 0 }}
        paginationMode="server"
        sortingMode="server"
        sortModel={sortModel}
        onSortModelChange={(model: GridSortModel) => {
          setSortModel(model);
          setPage(0);
        }}
        rowCount={total}
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
