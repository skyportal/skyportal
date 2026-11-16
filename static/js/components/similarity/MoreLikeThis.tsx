import { useState } from "react";
import { Link } from "react-router-dom";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

import Button from "../Button";
import ClassificationSelect from "../classification/ClassificationSelect";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useMoreLikeThisMutation } from "../../ducks/similarity";

const MoreLikeThis = () => {
  const { data: groupsData } = useGetGroupsQuery();
  const [classifications, setClassifications] = useState<string[]>([]);
  const [groupId, setGroupId] = useState<number | "">("");
  const [days, setDays] = useState(30);
  const [search, { data, isLoading, error }] = useMoreLikeThisMutation();
  const items = data?.items ?? [];

  return (
    <div>
      <Typography variant="h6">More like this</Typography>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          alignItems: "center",
          margin: "1rem 0",
        }}
      >
        <Box sx={{ width: "16rem" }}>
          <ClassificationSelect
            selectedClassifications={classifications}
            setSelectedClassifications={setClassifications}
          />
        </Box>
        <FormControl size="small" sx={{ width: "14rem" }}>
          <InputLabel>Group</InputLabel>
          <Select
            label="Group"
            value={groupId}
            onChange={(e) => setGroupId(e.target.value as number | "")}
          >
            <MenuItem value="">All</MenuItem>
            {(groupsData?.userAccessible || []).map((g) => (
              <MenuItem key={g.id} value={g.id}>
                {g.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          size="small"
          type="number"
          label="Days"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          slotProps={{ htmlInput: { min: 1, max: 365 } }}
          style={{ width: "7rem" }}
        />
        <Button
          primary
          disabled={
            isLoading || !classifications.length || !(days > 0 && days <= 365)
          }
          onClick={() =>
            search({
              classifications,
              days,
              ...(groupId !== "" ? { groupIds: [groupId] } : {}),
            })
          }
        >
          Search
        </Button>
        {isLoading && <CircularProgress color="secondary" size={24} />}
      </div>
      {error && <Typography variant="body2">Search failed</Typography>}
      {data && !isLoading && (
        <>
          <Typography variant="body2" color="text.secondary">
            {data.seeds_searched} of {data.seeds} seeds have an embedding
          </Typography>
          {items.length > 0 && (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Object</TableCell>
                  <TableCell align="right">Seeds</TableCell>
                  <TableCell align="right">Similarity</TableCell>
                  <TableCell>Nearest seed</TableCell>
                  <TableCell>AppleCiDEr</TableCell>
                  <TableCell align="right">z</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.obj_id}>
                    <TableCell>
                      <Link
                        to={
                          item.in_skyportal
                            ? `/source/${item.obj_id}`
                            : `/brokers/${data.broker_id}?objectId=${item.obj_id}`
                        }
                      >
                        {item.obj_id}
                      </Link>
                    </TableCell>
                    <TableCell align="right">{item.seeds}</TableCell>
                    <TableCell align="right">
                      {item.best_score.toFixed(3)}
                    </TableCell>
                    <TableCell>
                      <Link to={`/source/${item.nearest_seed}`}>
                        {item.nearest_seed}
                      </Link>
                    </TableCell>
                    <TableCell>{item.model_label ?? ""}</TableCell>
                    <TableCell align="right">
                      {item.redshift != null ? item.redshift.toFixed(4) : ""}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </>
      )}
    </div>
  );
};

export default MoreLikeThis;
