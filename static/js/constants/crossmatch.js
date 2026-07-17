const Gaia_DR3 = {
  name: "Gaia_DR3",
  type: [
    "null",
    {
      type: "record",
      name: "Gaia_DR3Match",
      fields: [
        {
          name: "_id",
          type: "double",
        },
        {
          name: "ra",
          type: "double",
        },
        {
          name: "dec",
          type: "double",
        },
        {
          name: "parallax",
          type: "double",
        },
        {
          name: "parallax_error",
          type: "double",
        },
        {
          name: "pm",
          type: "float",
        },
        {
          name: "pmra",
          type: "float",
        },
        {
          name: "pmra_error",
          type: "float",
        },
        {
          name: "pmdec",
          type: "float",
        },
        {
          name: "pmdec_error",
          type: "float",
        },
        {
          name: "phot_g_mean_mag",
          type: "double",
        },
        {
          name: "phot_bp_mean_mag",
          type: "double",
        },
        {
          name: "phot_rp_mean_mag",
          type: "double",
        },
        {
          name: "phot_g_n_obs",
          type: "int",
        },
        {
          name: "phot_bp_n_obs",
          type: "int",
        },
        {
          name: "phot_rp_n_obs",
          type: "int",
        },
        {
          name: "ruwe",
          type: "float",
        },
        {
          name: "phot_bp_rp_excess_factor",
          type: "float",
        },
        {
          name: "distance_arcsec",
          type: "float",
        },
      ],
    },
  ],
  default: null,
};

const milliquas_v8 = {
  name: "milliquas_v8",
  type: [
    "null",
    {
      type: "record",
      name: "Milliquas_v8Match",
      fields: [
        {
          name: "_id",
          type: "double",
        },
        {
          name: "Name",
          type: "string",
        },
        {
          name: "Descrip",
          type: "string",
        },
        {
          name: "Qpct",
          type: "float",
        },
        {
          name: "ra",
          type: "double",
        },
        {
          name: "dec",
          type: "double",
        },
        {
          name: "distance_arcsec",
          type: "float",
        },
      ],
    },
  ],
  default: null,
};

const NED = {
  name: "NED",
  type: [
    "null",
    {
      type: "record",
      name: "NEDMatch",
      fields: [
        {
          name: "_id",
          type: "double",
        },
        {
          name: "objname",
          type: "string",
        },
        {
          name: "ra",
          type: "double",
        },
        {
          name: "dec",
          type: "double",
        },
        {
          name: "objtype",
          type: "double",
        },
        {
          name: "z",
          type: "double",
        },
        {
          name: "z_unc",
          type: "double",
        },
        {
          name: "z_tech",
          type: "double",
        },
        {
          name: "z_qual",
          type: "double",
        },
        {
          name: "DistMpc",
          type: "string",
        },
        {
          name: "DistMpc_unc",
          type: "float",
        },
        {
          name: "ebv",
          type: "float",
        },
        {
          name: "m_Ks",
          type: "float",
        },
        {
          name: "m_Ks_unc",
          type: "float",
        },
        {
          name: "tMASSphot",
          type: "string",
        },
        {
          name: "Mstar",
          type: "float",
        },
        {
          name: "Mstar_unc",
          type: "float",
        },
        {
          name: "distance_arcsec",
          type: "float",
        },
        {
          name: "distance_kpc",
          type: "float",
        },
      ],
    },
  ],
  default: null,
};

const TWOMASS_PSC = {
  name: "2MASS_PSC",
  type: [
    "null",
    {
      type: "record",
      name: "TwoMASS_PSCMatch",
      fields: [
        {
          name: "_id",
          type: "double",
        },
        {
          name: "ra",
          type: "double",
        },
        {
          name: "dec",
          type: "double",
        },
        {
          name: "j_m",
          type: "double",
        },
        {
          name: "j_msigcom",
          type: "float",
        },
        {
          name: "j_snr",
          type: "float",
        },
        {
          name: "h_m",
          type: "double",
        },
        {
          name: "h_msigcom",
          type: "float",
        },
        {
          name: "h_snr",
          type: "float",
        },
        {
          name: "k_m",
          type: "double",
        },
        {
          name: "k_msigcom",
          type: "float",
        },
        {
          name: "k_snr",
          type: "float",
        },
        {
          name: "ndet",
          type: "int",
        },
        {
          name: "distance_arcsec",
          type: "float",
        },
      ],
    },
  ],
  default: null,
};

const GALEX = {
  name: "GALEX",
  type: [
    "null",
    {
      type: "record",
      name: "GALEXMatch",
      fields: [
        {
          name: "_id",
          type: "double",
        },
        {
          name: "ra",
          type: "double",
        },
        {
          name: "dec",
          type: "double",
        },
        {
          name: "fuv_mag",
          type: "float",
        },
        {
          name: "fuv_magerr",
          type: "float",
        },
        {
          name: "nuv_mag",
          type: "float",
        },
        {
          name: "nuv_magerr",
          type: "float",
        },
        {
          name: "fuv_exp",
          type: "float",
        },
        {
          name: "nuv_exp",
          type: "float",
        },
        {
          name: "obstype",
          type: "int",
        },
        {
          name: "band",
          type: "int",
        },
        {
          name: "distance_arcsec",
          type: "float",
        },
      ],
    },
  ],
  default: null,
};

const VSX = {
  name: "VSX",
  type: [
    "null",
    {
      type: "record",
      name: "VSXMatch",
      fields: [
        {
          name: "_id",
          type: "double",
        },
        {
          name: "name",
          type: "string",
        },
        {
          name: "var_flag",
          type: "int",
        },
        {
          name: "ra",
          type: "double",
        },
        {
          name: "dec",
          type: "double",
        },
        {
          name: "types",
          type: "string",
        },
        {
          name: "max",
          type: "double",
        },
        {
          name: "max_band",
          type: "string",
        },
        {
          name: "min_is_amplitude",
          type: "boolean",
        },
        {
          name: "min",
          type: "double",
        },
        {
          name: "min_band",
          type: "string",
        },
        {
          name: "epoch",
          type: "double",
        },
        {
          name: "period",
          type: "double",
        },
        {
          name: "spectral_type",
          type: "string",
        },
        {
          name: "distance_arcsec",
          type: "float",
        },
      ],
    },
  ],
  default: null,
};

const CatWISE2020 = {
  name: "CatWISE2020",
  type: [
    "null",
    {
      type: "record",
      name: "CatWISE2020Match",
      fields: [
        {
          name: "_id",
          type: "double",
        },
        {
          name: "source_name",
          type: "string",
        },
        {
          name: "ra",
          type: "double",
        },
        {
          name: "dec",
          type: "double",
        },
        {
          name: "sigra",
          type: "double",
        },
        {
          name: "sigdec",
          type: "double",
        },
        {
          name: "w1mpro",
          type: "double",
        },
        {
          name: "w1sigmpro",
          type: "double",
        },
        {
          name: "w2mpro",
          type: "double",
        },
        {
          name: "w2sigmpro",
          type: "double",
        },
        {
          name: "w1rchi2",
          type: "double",
        },
        {
          name: "w2rchi2",
          type: "double",
        },
        {
          name: "pmra",
          type: "double",
        },
        {
          name: "pmdec",
          type: "double",
        },
        {
          name: "sigpmra",
          type: "double",
        },
        {
          name: "sigpmdec",
          type: "double",
        },
        {
          name: "unwise_objid",
          type: "string",
        },
        {
          name: "distance_arcsec",
          type: "float",
        },
      ],
    },
  ],
  default: null,
};

const TNS = {
  name: "TNS",
  type: [
    "null",
    {
      type: "record",
      name: "TNSMatch",
      fields: [
        {
          name: "_id",
          type: "double",
        },
        {
          name: "name_prefix",
          type: "string",
        },
        {
          name: "name",
          type: "string",
        },
        {
          name: "ra",
          type: "double",
        },
        {
          name: "dec",
          type: "double",
        },
        {
          name: "type",
          type: "string",
        },
        {
          name: "redshift",
          type: "double",
        },
        {
          name: "discovery_mag",
          type: "float",
        },
        {
          name: "discovery_jd",
          type: "float",
        },
        {
          name: "internal_names",
          type: "array",
        },
        {
          name: "distance_arcsec",
          type: "float",
        },
      ],
    },
  ],
  default: null,
};

const LSPSC = {
  name: "LSPSC",
  type: [
    "null",
    {
      type: "record",
      name: "LSPSCMatch",
      fields: [
        {
          name: "_id",
          type: "double",
        },
        {
          name: "ra",
          type: "double",
        },
        {
          name: "dec",
          type: "double",
        },
        {
          name: "score",
          type: "float",
        },
        {
          name: "mag_white",
          type: "float",
        },
        {
          name: "distance_arcsec",
          type: "float",
        },
      ],
    },
  ],
  default: null,
};

export const ztf_crossmatch_fields = {
  name: "cross_matches",
  type: {
    type: "array",
    items: {
      type: "record",
      name: "CrossMatch",
      fields: [
        Gaia_DR3,
        milliquas_v8,
        NED,
        TWOMASS_PSC,
        GALEX,
        VSX,
        CatWISE2020,
        TNS,
      ],
    },
  },
};

export const lsst_crossmatch_fields = {
  name: "cross_matches",
  type: {
    type: "array",
    items: {
      type: "record",
      name: "CrossMatch",
      fields: [
        LSPSC,
        Gaia_DR3,
        milliquas_v8,
        NED,
        TWOMASS_PSC,
        GALEX,
        VSX,
        CatWISE2020,
        TNS,
      ],
    },
  },
};
