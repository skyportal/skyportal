import { useState } from "react";
import Link from "@mui/material/Link";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Popover from "@mui/material/Popover";
import type { BrokerHost } from "../../ducks/brokers";

const zDigits = (zErr: number | null) =>
  zErr ? Math.min(6, Math.max(1, Math.ceil(Math.abs(Math.log10(zErr))))) : 4;

const hostUrl = (host: BrokerHost) => {
  if (host.catalog === "NED" && host.objname) {
    return `https://ned.ipac.caltech.edu/byname?objname=${encodeURIComponent(
      host.objname,
    )}`;
  }
  if (host.ra == null || host.dec == null) return null;
  const layer = host.catalog === "LSDR9" ? "ls-dr9" : "ls-dr10";
  return `https://www.legacysurvey.org/viewer?ra=${host.ra}&dec=${host.dec}&layer=${layer}&zoom=16&mark=${host.ra},${host.dec}`;
};

const hostRows = (host: BrokerHost): [string, string][] => {
  const digits = zDigits(host.z_err);
  const rows: [string, string | null][] = [
    ["Catalog", host.catalog],
    [
      "Redshift",
      host.z != null
        ? `${host.z.toFixed(digits)}${
            host.z_err != null ? ` ± ${host.z_err.toFixed(digits)}` : ""
          }`
        : null,
    ],
    [
      "Distance",
      host.dist_mpc != null ? `${host.dist_mpc.toFixed(1)} Mpc` : null,
    ],
    [
      "Separation",
      host.sep_arcsec != null
        ? `${host.sep_arcsec.toFixed(2)}″${
            host.sep_kpc != null ? ` (${host.sep_kpc.toFixed(2)} kpc)` : ""
          }`
        : null,
    ],
    ["d_DLR", host.d_dlr != null ? host.d_dlr.toFixed(2) : null],
  ];
  return rows.filter((row): row is [string, string] => row[1] != null);
};

const BrokerHostChip = ({ host }: { host: BrokerHost | undefined }) => {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  if (!host) {
    return <Chip size="small" variant="outlined" label="None" />;
  }

  const name = host.objname || host.catalog || "Host";
  const url = hostUrl(host);

  return (
    <>
      <Chip
        size="small"
        color="success"
        label={
          host.z != null
            ? `${name} · z ${host.z.toFixed(zDigits(host.z_err))}`
            : name
        }
        onClick={(e) => setAnchor(e.currentTarget)}
      />
      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
      >
        <Box sx={{ p: 1.5, fontSize: "0.85rem" }}>
          <Box sx={{ fontWeight: "bold", mb: 1 }}>
            {url ? (
              <Link
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                underline="hover"
              >
                {name}
              </Link>
            ) : (
              name
            )}
          </Box>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "auto 1fr",
              columnGap: 2,
              rowGap: 0.25,
            }}
          >
            {hostRows(host).map(([label, value]) => (
              <Box key={label} sx={{ display: "contents" }}>
                <Box sx={{ color: "text.secondary" }}>{label}</Box>
                <Box>{value}</Box>
              </Box>
            ))}
          </Box>
        </Box>
      </Popover>
    </>
  );
};

export default BrokerHostChip;
