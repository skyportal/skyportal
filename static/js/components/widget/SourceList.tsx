import { ReactNode, useState } from "react";
import { Link } from "react-router-dom";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import MuiLink from "@mui/material/Link";
import Skeleton from "@mui/material/Skeleton";
import Typography from "@mui/material/Typography";
import ImageNotSupportedOutlined from "@mui/icons-material/ImageNotSupportedOutlined";

import DynamicTagDisplay from "./DynamicTagDisplay";
import ExpandableCell from "../ExpandableCell";
import { isPlaceholder } from "../thumbnail/ThumbnailList";
import { dec_to_dms, ra_to_hours } from "../../units";
import { useGetProfileQuery } from "../../ducks/profile";

const STAMP_SIZE = "4.75rem";

const latestClassification = (source: any) => {
  const classifications = source.classifications ?? [];
  let candidates = classifications.filter(
    (c: any) => c.probability > 0 && c.ml === false,
  );
  if (candidates.length === 0) {
    candidates = classifications.filter((c: any) => c.probability > 0);
  }
  const [latest] = [...candidates].sort((a: any, b: any) =>
    a.modified < b.modified ? 1 : -1,
  );
  return latest?.classification ?? null;
};

const tnsUrl = (tnsName: string) =>
  `https://www.wis-tns.org/object/${
    tnsName.trim().includes(" ") ? tnsName.split(" ")[1] : tnsName
  }`;

const SourceStamp = ({ source }: { source: any }) => {
  const invert = useGetProfileQuery().data?.preferences?.["invertThumbnails"];
  const [failed, setFailed] = useState(0);
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null);
  const thumbnail = (source.thumbnails ?? []).filter(
    (t: any) => !isPlaceholder(t.public_url),
  )[failed];
  const loaded = thumbnail && loadedSrc === thumbnail.public_url;

  return (
    <Box
      component={Link}
      to={`/source/${source.obj_id}`}
      sx={{
        position: "relative",
        flexShrink: 0,
        width: STAMP_SIZE,
        height: STAMP_SIZE,
        borderRadius: 2,
        overflow: "hidden",
        bgcolor: "action.hover",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {thumbnail ? (
        <>
          <Box
            component="img"
            src={thumbnail.public_url}
            alt={source.obj_id}
            loading="lazy"
            onLoad={() => setLoadedSrc(thumbnail.public_url)}
            onError={() => setFailed(failed + 1)}
            sx={{
              width: "100%",
              height: "100%",
              display: "block",
              opacity: loaded ? 1 : 0,
              transition: "opacity 0.3s",
              filter: invert && thumbnail.is_grayscale ? "invert(1)" : "none",
            }}
          />
          {!loaded && (
            <Skeleton
              variant="rectangular"
              sx={{ position: "absolute", inset: 0, height: "100%" }}
            />
          )}
        </>
      ) : (
        <ImageNotSupportedOutlined color="disabled" fontSize="small" />
      )}
    </Box>
  );
};

export const SourceListSkeleton = () => (
  <Box sx={{ overflow: "hidden" }}>
    {[...Array(4)].map((_, index) => (
      <Box key={index} sx={{ display: "flex", gap: 1.5, py: 1 }}>
        <Skeleton
          variant="rounded"
          width={STAMP_SIZE}
          height={STAMP_SIZE}
          sx={{ borderRadius: 2 }}
        />
        <Box sx={{ flex: 1 }}>
          <Skeleton variant="text" width="50%" height={22} />
          <Skeleton variant="text" width="30%" />
          <Skeleton variant="text" width="60%" />
        </Box>
      </Box>
    ))}
  </Box>
);

interface SourceRowProps {
  source: any;
  testId: string;
  meta: ReactNode;
  displayTNS?: boolean;
  showGroups?: boolean;
}

export const SourceRow = ({
  source,
  testId,
  meta,
  displayTNS = true,
  showGroups = false,
}: SourceRowProps) => {
  const classification = latestClassification(source);
  const tnsName = displayTNS && source.tns_name?.length > 0 && source.tns_name;

  return (
    <Box
      data-testid={testId}
      sx={{
        display: "flex",
        gap: 1.5,
        p: 1,
        mx: -1,
        borderRadius: 2,
        transition: "background-color 0.15s",
        "&:hover": { bgcolor: "action.hover" },
      }}
    >
      <SourceStamp source={source} />
      <Box
        sx={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          gap: 0.25,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "baseline", gap: 1 }}>
          <MuiLink
            component={Link}
            to={`/source/${source.obj_id}`}
            noWrap
            sx={{ minWidth: 0, fontWeight: 600 }}
          >
            <span>{source.obj_id}</span>
          </MuiLink>
          <Typography
            component="span"
            variant="caption"
            color="text.secondary"
            sx={{ ml: "auto", flexShrink: 0, whiteSpace: "nowrap" }}
          >
            {meta}
          </Typography>
        </Box>
        {(classification || tnsName) && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.75,
              minWidth: 0,
            }}
          >
            {classification && (
              <Typography variant="body2" noWrap sx={{ fontWeight: 500 }}>
                {classification}
              </Typography>
            )}
            {tnsName && (
              <Chip
                label={tnsName}
                size="small"
                color={tnsName.includes("SN") ? "primary" : "default"}
                onClick={() => window.open(tnsUrl(tnsName), "_blank")}
                sx={{ height: 20, fontSize: "0.7rem", fontWeight: 600 }}
              />
            )}
          </Box>
        )}
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            display: "flex",
            columnGap: 1.5,
            flexWrap: "wrap",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          <span>{`α ${ra_to_hours(source.ra)}`}</span>
          <span>{`δ ${dec_to_dms(source.dec)}`}</span>
        </Typography>
        {showGroups && source.groups?.length > 0 && (
          <Box sx={{ mt: 0.25 }}>
            <ExpandableCell
              maxVisible={2}
              items={source.groups.map((group: any) => (
                <Chip
                  key={group.id}
                  label={group.name}
                  size="small"
                  variant="outlined"
                  component={Link}
                  to={`/group/${group.id}`}
                  clickable
                  sx={{ height: 20, maxWidth: "10rem", fontSize: "0.7rem" }}
                />
              ))}
            />
          </Box>
        )}
        <DynamicTagDisplay source={source} />
      </Box>
    </Box>
  );
};
