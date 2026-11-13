import { Link } from "react-router-dom";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";

import VegaPhotometry from "../plot/VegaPhotometry";
import {
  useGetSimilarSourcesQuery,
  type SimilarSource,
} from "../../ducks/similarity";

const thumbnailStyle = { width: "12rem", height: "5rem", minHeight: "5rem" };

const NeighborClass = ({ neighbor }: { neighbor: SimilarSource }) => {
  if (neighbor.classification) {
    return <>{neighbor.classification.classification}</>;
  }
  if (neighbor.model_label) {
    return (
      <Tooltip title="AppleCiDEr">
        <Typography variant="body2" color="text.secondary" component="span">
          {neighbor.model_label}
        </Typography>
      </Tooltip>
    );
  }
  return null;
};

const SimilarObjects = ({ objId }: { objId: string }) => {
  const { data, isLoading, error } = useGetSimilarSourcesQuery({ objId });

  if (isLoading) return <CircularProgress color="secondary" size={24} />;
  if (error) return <Typography variant="body2">Search failed</Typography>;
  if (!data?.neighbors?.length)
    return <Typography variant="body2">No neighbors</Typography>;

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Object</TableCell>
          <TableCell align="right">Similarity</TableCell>
          <TableCell>Class</TableCell>
          <TableCell align="right">z</TableCell>
          <TableCell>Light curve</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {data.neighbors.map((neighbor) => (
          <TableRow key={neighbor.obj_id}>
            <TableCell>
              <Link
                to={
                  neighbor.in_skyportal
                    ? `/source/${neighbor.obj_id}`
                    : `/brokers/${data.broker_id}?objectId=${neighbor.obj_id}`
                }
              >
                {neighbor.obj_id}
              </Link>
            </TableCell>
            <TableCell align="right">{neighbor.score.toFixed(3)}</TableCell>
            <TableCell>
              <NeighborClass neighbor={neighbor} />
            </TableCell>
            <TableCell align="right">
              {neighbor.redshift != null ? neighbor.redshift.toFixed(4) : ""}
            </TableCell>
            <TableCell>
              {neighbor.in_skyportal && (
                <VegaPhotometry
                  sourceId={neighbor.obj_id}
                  controls={false}
                  style={thumbnailStyle}
                />
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default SimilarObjects;
