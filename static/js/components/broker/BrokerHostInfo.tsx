import type { BrokerHost } from "../../ducks/brokers";

const zDigits = (zErr: number | null) =>
  zErr ? Math.min(6, Math.max(1, Math.ceil(Math.abs(Math.log10(zErr))))) : 4;

const BrokerHostInfo = ({ host }: { host: BrokerHost }) => {
  const digits = zDigits(host.z_err);
  const name = [host.objname, host.catalog && `(${host.catalog})`]
    .filter(Boolean)
    .join(" ");
  const separation = [
    host.sep_arcsec != null && `${host.sep_arcsec.toFixed(1)}″`,
    host.sep_kpc != null && `${host.sep_kpc.toFixed(1)} kpc`,
  ]
    .filter(Boolean)
    .join(" / ");
  const parts = [
    name,
    host.z != null &&
      `z = ${host.z.toFixed(digits)}${
        host.z_err != null ? ` ± ${host.z_err.toFixed(digits)}` : ""
      }`,
    host.dist_mpc != null && `${host.dist_mpc.toFixed(1)} Mpc`,
    separation && `sep ${separation}`,
    host.d_dlr != null && `d_DLR ${host.d_dlr.toFixed(2)}`,
  ].filter(Boolean);

  return <span>{parts.join(" · ")}</span>;
};

export default BrokerHostInfo;
