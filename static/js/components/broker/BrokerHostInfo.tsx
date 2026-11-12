import type { BrokerHost } from "../../ducks/brokers";

export const zDigits = (zErr: number | null) =>
  zErr ? Math.min(6, Math.max(1, Math.ceil(Math.abs(Math.log10(zErr))))) : 4;

export const hostUrl = (host: BrokerHost) => {
  if (host.catalog === "NED" && host.objname) {
    return `https://ned.ipac.caltech.edu/byname?objname=${encodeURIComponent(
      host.objname,
    )}`;
  }
  if (host.ra == null || host.dec == null) return null;
  const layer = host.catalog === "LSDR9" ? "ls-dr9" : "ls-dr10";
  return `https://www.legacysurvey.org/viewer?ra=${host.ra}&dec=${host.dec}&layer=${layer}&zoom=16&mark=${host.ra},${host.dec}`;
};

const BrokerHostInfo = ({ host }: { host: BrokerHost }) => {
  const digits = zDigits(host.z_err);
  const url = hostUrl(host);
  const separation = [
    host.sep_arcsec != null && `${host.sep_arcsec.toFixed(1)}″`,
    host.sep_kpc != null && `${host.sep_kpc.toFixed(1)} kpc`,
  ]
    .filter(Boolean)
    .join(" / ");
  const details = [
    host.z != null &&
      `z = ${host.z.toFixed(digits)}${
        host.z_err != null ? ` ± ${host.z_err.toFixed(digits)}` : ""
      }`,
    host.dist_mpc != null && `${host.dist_mpc.toFixed(1)} Mpc`,
    separation && `sep ${separation}`,
    host.d_dlr != null && `d_DLR ${host.d_dlr.toFixed(2)}`,
  ].filter(Boolean);

  return (
    <span>
      {host.objname &&
        (url ? (
          <a href={url} target="_blank" rel="noopener noreferrer">
            {host.objname}
          </a>
        ) : (
          host.objname
        ))}
      {host.catalog && ` (${host.catalog})`}
      {details.length > 0 &&
        `${host.objname || host.catalog ? " · " : ""}${details.join(" · ")}`}
    </span>
  );
};

export default BrokerHostInfo;
