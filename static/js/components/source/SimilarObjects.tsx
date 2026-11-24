import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import VegaPhotometry from "../plot/VegaPhotometry";
import {
  useGetSimilarSourcesQuery,
  type SimilarSource,
} from "../../ducks/similarity";

const plotStyle = {
  width: "100%",
  height: "15.5rem",
  minHeight: "15.5rem",
};

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
  const [openIds, setOpenIds] = useState<string[]>([]);

  if (isLoading) return <CircularProgress color="secondary" size={24} />;
  if (error) return <Typography variant="body2">Search failed</Typography>;
  if (!data?.neighbors?.length) {
    const messages: Record<string, string> = {
      survey: `Not searched: similarity search covers ${(data?.surveys ?? []).join(", ")} objects only.`,
      no_embedding: "Not searched: no embedding is stored for this object.",
    };
    const message = messages[data?.no_neighbors_reason ?? ""];
    return (
      <Typography variant="body2" color="text.secondary">
        {message ?? "No similar objects found."}
      </Typography>
    );
  }

  const toggle = (id: string) =>
    setOpenIds((ids) =>
      ids.includes(id) ? ids.filter((i) => i !== id) : [...ids, id],
    );
  const plottableIds = data.neighbors
    .filter((neighbor) => neighbor.in_skyportal)
    .map((neighbor) => neighbor.obj_id);
  const allOpen =
    plottableIds.length > 0 && plottableIds.every((id) => openIds.includes(id));

  return (
    <TableContainer>
      <Table
        size="small"
        sx={{
          "& th, & td": { px: 1 },
          "& th": { color: "text.secondary", whiteSpace: "nowrap" },
        }}
      >
        <TableHead>
          <TableRow>
            <TableCell>Object</TableCell>
            <TableCell align="right">Similarity</TableCell>
            <TableCell>Class</TableCell>
            <TableCell align="right">z</TableCell>
            <TableCell padding="checkbox">
              {plottableIds.length > 0 && (
                <IconButton
                  size="small"
                  aria-label={
                    allOpen ? "Hide all light curves" : "Show all light curves"
                  }
                  onClick={() => setOpenIds(allOpen ? [] : plottableIds)}
                >
                  <ExpandMoreIcon
                    fontSize="small"
                    sx={{
                      transform: allOpen ? "rotate(180deg)" : "none",
                      transition: "transform 0.2s",
                    }}
                  />
                </IconButton>
              )}
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.neighbors.map((neighbor) => {
            const open = openIds.includes(neighbor.obj_id);
            return (
              <Fragment key={neighbor.obj_id}>
                <TableRow
                  hover={neighbor.in_skyportal}
                  onClick={
                    neighbor.in_skyportal
                      ? () => toggle(neighbor.obj_id)
                      : undefined
                  }
                  sx={{
                    cursor: neighbor.in_skyportal ? "pointer" : "default",
                    ...(open && { "& > td": { borderBottom: "none" } }),
                  }}
                >
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    <Link
                      to={
                        neighbor.in_skyportal
                          ? `/source/${neighbor.obj_id}`
                          : `/brokers/${data.broker_id}?objectId=${neighbor.obj_id}`
                      }
                      onClick={(e) => e.stopPropagation()}
                    >
                      {neighbor.obj_id}
                    </Link>
                  </TableCell>
                  <TableCell align="right">
                    {neighbor.score.toFixed(3)}
                  </TableCell>
                  <TableCell>
                    <NeighborClass neighbor={neighbor} />
                  </TableCell>
                  <TableCell align="right">
                    {neighbor.redshift != null
                      ? neighbor.redshift.toFixed(4)
                      : ""}
                  </TableCell>
                  <TableCell padding="checkbox">
                    {neighbor.in_skyportal && (
                      <IconButton
                        size="small"
                        aria-label={open ? "Hide light curve" : "Light curve"}
                      >
                        <ExpandMoreIcon
                          fontSize="small"
                          sx={{
                            transform: open ? "rotate(180deg)" : "none",
                            transition: "transform 0.2s",
                          }}
                        />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
                {open && (
                  <TableRow>
                    <TableCell colSpan={5} sx={{ pt: 0 }}>
                      <div style={{ width: 0, minWidth: "100%" }}>
                        <VegaPhotometry
                          sourceId={neighbor.obj_id}
                          controls={false}
                          style={plotStyle}
                        />
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default SimilarObjects;
