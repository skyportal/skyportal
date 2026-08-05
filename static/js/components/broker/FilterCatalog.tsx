import { useState } from "react";
import { Link } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MuiLink from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  useAttachFilterToBrokerMutation,
  useGetBrokersQuery,
  useGetFilterCatalogQuery,
} from "../../ducks/brokers";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";

const PAGE_SIZES = [10, 25, 50];

const FilterCatalog = ({ brokerId }: { brokerId?: number }) => {
  const [page, setPage] = useState(0);
  const [numPerPage, setNumPerPage] = useState(25);
  const [name, setName] = useState("");
  const [groupID, setGroupID] = useState<number | "">("");
  const [streamID, setStreamID] = useState<number | "">("");
  const [brokerID, setBrokerID] = useState<number | "" | "none">("");
  const [targets, setTargets] = useState<Record<number, number>>({});

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

  const groupList = groups?.userAccessible || [];
  const streamList = (streams as { id: number; name: string }[]) || [];
  const brokerList = brokers || [];
  const brokerName = (id: number) =>
    brokerList.find((b) => b.id === id)?.name ?? `broker ${id}`;
  const groupName = (id: number) =>
    groupList.find((g) => g.id === id)?.name ?? `group ${id}`;
  const streamName = (id: number) =>
    streamList.find((s) => s.id === id)?.name ?? `stream ${id}`;
  // Only brokers that accept filters can be attached to.
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

  const filters = data?.filters || [];

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

      <Paper variant="outlined" sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Group</TableCell>
              <TableCell>Stream</TableCell>
              {brokerId ? null : (
                <>
                  <TableCell>Broker</TableCell>
                  <TableCell align="right">Attach to</TableCell>
                </>
              )}
            </TableRow>
          </TableHead>
          <TableBody>
            {filters.length === 0 && (
              <TableRow>
                <TableCell colSpan={brokerId ? 3 : 5}>
                  <Typography variant="body2" color="text.secondary">
                    {isFetching ? "Loading…" : "No filter matches this search."}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
            {filters.map((f) => (
              <TableRow key={f.id} hover>
                <TableCell>
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
                </TableCell>
                <TableCell>{groupName(f.group_id)}</TableCell>
                <TableCell>{streamName(f.stream_id)}</TableCell>
                {brokerId ? null : (
                  <>
                    <TableCell>
                      {f.broker_id ? brokerName(f.broker_id) : "—"}
                    </TableCell>
                    <TableCell align="right">
                      {f.broker_id ? null : (
                        <Box
                          sx={{
                            display: "flex",
                            gap: 1,
                            justifyContent: "flex-end",
                          }}
                        >
                          <FormControl size="small" sx={{ minWidth: 180 }}>
                            <InputLabel id={`attach-broker-${f.id}`}>
                              Broker
                            </InputLabel>
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
                        </Box>
                      )}
                    </TableCell>
                  </>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={data?.totalMatches ?? 0}
          page={page}
          onPageChange={(_e, p) => setPage(p)}
          rowsPerPage={numPerPage}
          rowsPerPageOptions={PAGE_SIZES}
          onRowsPerPageChange={(e) => {
            setNumPerPage(Number(e.target.value));
            setPage(0);
          }}
        />
      </Paper>
    </Box>
  );
};

export default FilterCatalog;
