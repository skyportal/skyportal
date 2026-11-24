import { Fragment, ReactNode, useState } from "react";
import { Link } from "react-router-dom";

import Box from "@mui/material/Box";
import MuiLink from "@mui/material/Link";
import Skeleton from "@mui/material/Skeleton";
import Typography from "@mui/material/Typography";
import { alpha, lighten } from "@mui/material/styles";
import ImageNotSupportedOutlined from "@mui/icons-material/ImageNotSupportedOutlined";

import DynamicTagDisplay from "./DynamicTagDisplay";
import { isPlaceholder } from "../thumbnail/ThumbnailList";
import { dec_to_dms, ra_to_hours } from "../../units";
import { useGetProfileQuery } from "../../ducks/profile";

const STAMP_SIZE = "4rem";

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

const pillSx = {
  px: 0.75,
  py: 0.125,
  borderRadius: 1,
  fontSize: "0.72rem",
  fontWeight: 600,
  lineHeight: 1.5,
  whiteSpace: "nowrap",
} as const;

export const SourceRow = ({
  source,
  testId,
  meta,
  displayTNS = true,
  showGroups = false,
}: SourceRowProps) => {
  const classification = latestClassification(source);
  const tnsName = displayTNS && source.tns_name?.length > 0 && source.tns_name;
  const groups: any[] = (showGroups && source.groups) || [];

  return (
    <Box
      data-testid={testId}
      sx={{
        display: "flex",
        gap: 1.5,
        py: 1.25,
        "& + &": { borderTop: 1, borderColor: "divider" },
      }}
    >
      <SourceStamp source={source} />
      <Box
        sx={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          gap: 0.5,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
          <MuiLink
            component={Link}
            to={`/source/${source.obj_id}`}
            noWrap
            sx={{ minWidth: 0, fontWeight: 600 }}
          >
            <span>{source.obj_id}</span>
          </MuiLink>
          {tnsName && (
            <MuiLink
              href={tnsUrl(tnsName)}
              target="_blank"
              rel="noreferrer"
              underline="none"
              sx={{
                ...pillSx,
                ...(tnsName.includes("SN")
                  ? { bgcolor: "primary.main", color: "primary.contrastText" }
                  : { bgcolor: "action.selected", color: "text.primary" }),
              }}
            >
              {tnsName}
            </MuiLink>
          )}
          <Typography
            component="span"
            variant="caption"
            color="text.secondary"
            sx={{ ml: "auto", flexShrink: 0, whiteSpace: "nowrap" }}
          >
            {meta}
          </Typography>
        </Box>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            columnGap: 1.25,
            rowGap: 0.5,
          }}
        >
          {classification && (
            <Box
              component="span"
              sx={(theme) => ({
                ...pillSx,
                color:
                  theme.palette.mode === "dark"
                    ? lighten(theme.palette.primary.main, 0.5)
                    : theme.palette.primary.main,
                bgcolor: alpha(theme.palette.primary.main, 0.12),
              })}
            >
              {classification}
            </Box>
          )}
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              display: "flex",
              columnGap: 1.25,
              fontVariantNumeric: "tabular-nums",
              whiteSpace: "nowrap",
            }}
          >
            <span>{`α ${ra_to_hours(source.ra)}`}</span>
            <span>{`δ ${dec_to_dms(source.dec)}`}</span>
          </Typography>
        </Box>
        {groups.length > 0 && (
          <Typography
            variant="caption"
            color="text.secondary"
            noWrap
            title={groups.map((group) => group.name).join(", ")}
          >
            {groups.map((group, index) => (
              <Fragment key={group.id}>
                {index > 0 && ", "}
                <MuiLink
                  component={Link}
                  to={`/group/${group.id}`}
                  color="inherit"
                  underline="hover"
                  sx={{ fontWeight: 400 }}
                >
                  {group.name}
                </MuiLink>
              </Fragment>
            ))}
          </Typography>
        )}
        <DynamicTagDisplay source={source} />
      </Box>
    </Box>
  );
};
