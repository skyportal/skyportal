import { useGetProfileQuery } from "../../../ducks/profile";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityIcon from "@mui/icons-material/Visibility";
import Link from "@mui/material/Link";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import InfoIcon from "@mui/icons-material/InfoOutlined";
import moment from "moment";
import {
  useDeletePublicSourcePageMutation,
  useFetchPublicSourcePagesQuery,
} from "../../../ducks/public_pages/public_source_page";
import { userLabel } from "../../../utils/format";

interface SourcePublishHistoryProps {
  sourceId: string;
}

const SourcePublishHistory = ({ sourceId }: SourcePublishHistoryProps) => {
  const manageSourcesAccess =
    useGetProfileQuery().data?.permissions?.includes("Manage sources");
  const { data: versions = [], isLoading: loading } =
    useFetchPublicSourcePagesQuery(sourceId) as {
      data: any[];
      isLoading: boolean;
    };
  const [deletePublicSourcePage] = useDeletePublicSourcePageMutation();

  if (versions.length === 0) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          py: 2,
          color: "text.secondary",
        }}
      >
        {loading ? (
          <CircularProgress size={24} />
        ) : (
          "No public page available yet!"
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, px: 0.5 }}>
      {versions.map((version) => (
        <Box
          key={`version_${version.id}`}
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 1,
            border: 1,
            borderColor: "divider",
            borderRadius: 2,
            py: 0.5,
            px: 1,
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              {moment(version.created_at).format("MM/DD/YY HH:mm")} UTC
              <Tooltip
                title={
                  <Box sx={{ display: "flex", flexDirection: "column" }}>
                    <span>Photometry: {version.options.photometry}</span>
                    <span>Spectroscopy: {version.options.spectroscopy}</span>
                    <span>
                      Classifications: {version.options.classifications}
                    </span>
                  </Box>
                }
                placement="right"
              >
                <InfoIcon fontSize="small" color="primary" />
              </Tooltip>
            </Box>
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                columnGap: 1,
                fontSize: "0.8rem",
                color: "text.secondary",
              }}
            >
              {version.created_by && (
                <span>by {userLabel(version.created_by)}</span>
              )}
              {version.release_link_name ? (
                <Link
                  href={`/public/releases/${version.release_link_name}`}
                  target="_blank"
                  underline="hover"
                >
                  {version.release_link_name}
                </Link>
              ) : (
                <span>No release</span>
              )}
            </Box>
          </Box>
          <Box sx={{ display: "flex", flexShrink: 0 }}>
            <Tooltip title="Open">
              <IconButton
                href={`/public${
                  version.release_link_name
                    ? `/releases/${version.release_link_name}`
                    : ""
                }/sources/${sourceId}/version/${version?.hash}`}
                target="_blank"
                color="primary"
              >
                <VisibilityIcon />
              </IconButton>
            </Tooltip>
            {manageSourcesAccess && (
              <Tooltip title="Delete">
                <IconButton
                  onClick={() => deletePublicSourcePage(version.id)}
                  color="primary"
                >
                  <DeleteIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>
      ))}
    </Box>
  );
};

export default SourcePublishHistory;
