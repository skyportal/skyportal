import { useState } from "react";
import Link from "@mui/material/Link";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Popover from "@mui/material/Popover";
import type { BrokerHost } from "../../ducks/brokers";

export const zDigits = (zErr: number | null | undefined) =>
  zErr ? Math.min(6, Math.max(1, Math.ceil(Math.abs(Math.log10(zErr))))) : 4;

export const hostUrl = ({
  catalog,
  objname,
  ra,
  dec,
}: {
  catalog?: string | null | undefined;
  objname?: string | null;
  ra?: number | null;
  dec?: number | null;
}) => {
  if (catalog === "NED" && objname) {
    return `https://ned.ipac.caltech.edu/byname?objname=${encodeURIComponent(
      objname,
    )}`;
  }
  if (ra == null || dec == null) return null;
  const layer = catalog === "LSDR9" ? "ls-dr9" : "ls-dr10";
  return `https://www.legacysurvey.org/viewer?ra=${ra}&dec=${dec}&layer=${layer}&zoom=16&mark=${ra},${dec}`;
};

const formatZ = (z: number, zErr: number | null | undefined) => {
  const digits = zDigits(zErr);
  return `${z.toFixed(digits)}${zErr != null ? ` ± ${zErr.toFixed(digits)}` : ""}`;
};

const formatSeparation = (
  arcsec: number | null | undefined,
  kpc: number | null | undefined,
) => {
  if (arcsec == null) return null;
  return `${arcsec.toFixed(2)}″${kpc != null ? ` (${kpc.toFixed(1)} kpc)` : ""}`;
};

export interface HostSummary {
  name: string;
  tag?: string | undefined;
  heading?: string | undefined;
  primary?: boolean | undefined;
  extraRows?: [string, string][] | undefined;
  z?: number | null | undefined;
  zErr?: number | null | undefined;
  sepArcsec?: number | null | undefined;
  sepKpc?: number | null | undefined;
  distMpc?: number | null | undefined;
  catalog?: string | null | undefined;
  dDlr?: number | null | undefined;
  url?: string | null | undefined;
}

const detailRows = (host: HostSummary): [string, string][] => {
  const rows: [string, string | null | undefined][] = [
    ["Catalog", host.catalog],
    ["Redshift", host.z != null ? formatZ(host.z, host.zErr) : null],
    [
      "Distance",
      host.distMpc != null ? `${host.distMpc.toFixed(1)} Mpc` : null,
    ],
    ["Separation", formatSeparation(host.sepArcsec, host.sepKpc)],
    ["d_DLR", host.dDlr != null ? host.dDlr.toFixed(2) : null],
    ...(host.extraRows ?? []),
  ];
  return rows.filter((row): row is [string, string] => row[1] != null);
};

export const HostChip = ({
  host,
  onDelete,
}: {
  host: HostSummary;
  onDelete?: (() => void) | undefined;
}) => {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const heading = host.heading ?? host.tag;
  const meta = [
    host.z != null ? `z ${host.z.toFixed(zDigits(host.zErr))}` : null,
    host.sepArcsec != null ? `${host.sepArcsec.toFixed(1)}″` : null,
    host.sepKpc != null ? `${host.sepKpc.toFixed(1)} kpc` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <>
      <Chip
        size="small"
        variant={host.primary ? "filled" : "outlined"}
        onClick={(e) => setAnchor(e.currentTarget)}
        onDelete={onDelete}
        sx={host.primary ? {} : { bgcolor: "background.paper" }}
        label={
          <Box
            component="span"
            sx={{ display: "inline-flex", alignItems: "baseline", gap: 0.75 }}
          >
            {host.tag && (
              <Box
                component="span"
                sx={{
                  fontSize: "0.65rem",
                  fontWeight: 600,
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                  color: "text.secondary",
                }}
              >
                {host.tag}
              </Box>
            )}
            <Box component="span" sx={{ fontWeight: 600 }}>
              {host.name}
            </Box>
            {meta && (
              <Box
                component="span"
                sx={{
                  color: "text.secondary",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {meta}
              </Box>
            )}
          </Box>
        }
      />
      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        transformOrigin={{ vertical: -6, horizontal: "left" }}
      >
        <Box sx={{ p: 1.5, minWidth: 200, fontSize: "0.85rem" }}>
          {heading && (
            <Box
              sx={{
                fontSize: "0.65rem",
                fontWeight: 600,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: "text.secondary",
              }}
            >
              {heading}
            </Box>
          )}
          <Box sx={{ fontWeight: 600, fontSize: "0.95rem", mb: 1 }}>
            {host.url ? (
              <Link
                href={host.url}
                target="_blank"
                rel="noopener noreferrer"
                underline="hover"
              >
                {host.name}
              </Link>
            ) : (
              host.name
            )}
          </Box>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "auto 1fr",
              columnGap: 2,
              rowGap: 0.5,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {detailRows(host).map(([label, value]) => (
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

export const brokerHostSummary = (
  host: BrokerHost,
  tag?: string,
): HostSummary => ({
  name: host.objname || host.catalog || "Host",
  tag,
  z: host.z,
  zErr: host.z_err,
  sepArcsec: host.sep_arcsec,
  sepKpc: host.sep_kpc,
  distMpc: host.dist_mpc,
  catalog: host.catalog,
  dDlr: host.d_dlr,
  url: hostUrl(host),
});

const BrokerHostChip = ({ host }: { host: BrokerHost | undefined }) => {
  if (!host) {
    return (
      <Box component="span" sx={{ color: "text.secondary" }}>
        None
      </Box>
    );
  }
  return <HostChip host={brokerHostSummary(host)} />;
};

export default BrokerHostChip;
