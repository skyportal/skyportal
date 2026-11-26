import { ReactNode } from "react";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import UpdateSourceCoordinates from "./UpdateSourceCoordinates";
import { useIsReadOnly } from "../../ducks/profile";
import { dec_to_dms, ra_to_hours } from "../../units";
import { Source } from "../../types";

const CoordLabel = ({ children }: { children: ReactNode }) => (
  <Box component="span" sx={{ color: "text.disabled", mr: 0.5 }}>
    {children}
  </Box>
);

interface SourceCoordinatesProps {
  source: Source & {
    adjusted_position?: {
      ra?: number;
      dec?: number;
      gal_lat?: number;
      gal_lon?: number;
      ebv?: number;
      separation?: number;
    };
    ebv?: number;
  };
}

const SourceCoordinates = ({ source }: SourceCoordinatesProps) => {
  const isReadOnly = useIsReadOnly();
  const ra = source?.adjusted_position?.ra || source.ra;
  const dec = source?.adjusted_position?.dec || source.dec;
  const gal_lon = source?.adjusted_position?.gal_lon || source.gal_lon;
  const gal_lat = source?.adjusted_position?.gal_lat || source.gal_lat;
  const ebv = source?.adjusted_position?.ebv || source.ebv;

  const title =
    (source?.adjusted_position?.separation ?? 0) > 0
      ? `The coordinates displayed here have been re-computed using the object's photometry (${source.adjusted_position!.separation!.toFixed(
          2,
        )}" from the original)`
      : "";

  return (
    <Tooltip title={title} placement="top">
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          columnGap: 1.5,
          rowGap: 0.25,
          mb: 0.25,
          fontVariantNumeric: "tabular-nums",
          "& .edit-position": {
            opacity: 0,
            transition: "opacity 0.15s",
            "& .MuiIconButton-root": { p: "1px", color: "text.secondary" },
            "& .MuiSvgIcon-root": { fontSize: "0.75rem" },
          },
          "&:hover .edit-position, &:focus-within .edit-position": {
            opacity: 1,
          },
          "@media (hover: none)": { "& .edit-position": { opacity: 1 } },
        }}
      >
        <Box component="span" sx={{ fontWeight: 500 }}>
          {`${ra_to_hours(ra, ":")} ${dec_to_dms(dec, ":")}`}
        </Box>
        <span>
          <CoordLabel>&alpha;, &delta;</CoordLabel>
          {ra.toFixed(6)}, {dec.toFixed(6)}
        </span>
        <span>
          <CoordLabel>
            <i>l</i>, <i>b</i>
          </CoordLabel>
          {gal_lon?.toFixed(6)}, {gal_lat?.toFixed(6)}
        </span>
        <Box
          component="span"
          sx={{ display: "inline-flex", alignItems: "center" }}
        >
          {ebv != null && (
            <>
              <CoordLabel>E(B-V)</CoordLabel>
              {ebv.toFixed(2)}
            </>
          )}
          {!isReadOnly && (
            <span className="edit-position">
              <UpdateSourceCoordinates source={source} />
            </span>
          )}
        </Box>
      </Box>
    </Tooltip>
  );
};

export default SourceCoordinates;
