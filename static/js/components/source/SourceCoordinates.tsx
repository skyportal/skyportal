import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import UpdateSourceCoordinates from "./UpdateSourceCoordinates";
import FieldLabel from "./FieldLabel";
import { dec_to_dms, ra_to_hours } from "../../units";
import { Source } from "../../types";

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
  downMd?: boolean;
}

const SourceCoordinates = ({
  source,
  downMd = false,
}: SourceCoordinatesProps) => {
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
      : "The coordinates displayed here are the original coordinates of the object";

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
        }}
      >
        <Box
          component="span"
          sx={{ fontWeight: 600, fontSize: downMd ? "1rem" : "1.1rem" }}
        >
          {`${ra_to_hours(ra, ":")} ${dec_to_dms(dec, ":")}`}
        </Box>
        <span>
          <FieldLabel>&alpha;, &delta;</FieldLabel>
          {ra.toFixed(6)}, {dec.toFixed(6)}
        </span>
        <span>
          <FieldLabel>
            <i>l</i>, <i>b</i>
          </FieldLabel>
          {gal_lon?.toFixed(6)}, {gal_lat?.toFixed(6)}
        </span>
        <Box
          component="span"
          sx={{ display: "inline-flex", alignItems: "center" }}
        >
          {ebv != null && (
            <>
              <FieldLabel>E(B-V)</FieldLabel>
              {ebv.toFixed(2)}
            </>
          )}
          <UpdateSourceCoordinates source={source} />
        </Box>
      </Box>
    </Tooltip>
  );
};

export default SourceCoordinates;
