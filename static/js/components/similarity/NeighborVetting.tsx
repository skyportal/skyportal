import { useState } from "react";
import { Link } from "react-router-dom";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";

import Button from "../Button";
import { useLazyGetSimilarityVettingQuery } from "../../ducks/similarity";

const NeighborVetting = () => {
  const [days, setDays] = useState(1);
  const [search, { data, isFetching, error }] =
    useLazyGetSimilarityVettingQuery();
  const items = data?.items ?? [];

  return (
    <div>
      <Typography variant="h6">Neighbor vetting</Typography>
      <div
        style={{
          display: "flex",
          gap: "1rem",
          alignItems: "center",
          margin: "1rem 0",
        }}
      >
        <TextField
          size="small"
          type="number"
          label="Days"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          slotProps={{ htmlInput: { min: 0.5, max: 30, step: 0.5 } }}
          style={{ width: "7rem" }}
        />
        <Button
          primary
          disabled={isFetching || !(days > 0 && days <= 30)}
          onClick={() => search({ days })}
        >
          Search
        </Button>
        {isFetching && <CircularProgress color="secondary" size={24} />}
      </div>
      {error && <Typography variant="body2">Search failed</Typography>}
      {data && !isFetching && (
        <>
          <Typography variant="body2" color="text.secondary">
            {items.length} of {data.checked} sources
          </Typography>
          {items.length > 0 && (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Source</TableCell>
                  <TableCell>Class</TableCell>
                  <TableCell align="right">Agreeing</TableCell>
                  <TableCell>Neighbors</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.obj_id}>
                    <TableCell>
                      <Link to={`/source/${item.obj_id}`}>{item.obj_id}</Link>
                    </TableCell>
                    <TableCell>{item.classification}</TableCell>
                    <TableCell align="right">
                      {Math.round(item.agreement * item.labeled_neighbors)}/
                      {item.labeled_neighbors}
                    </TableCell>
                    <TableCell>
                      {Object.entries(item.neighbor_classes ?? {})
                        .map(([name, count]) => `${name} ${count}`)
                        .join(", ")}
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

export default NeighborVetting;
