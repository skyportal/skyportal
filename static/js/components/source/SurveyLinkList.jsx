import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import makeStyles from "@mui/styles/makeStyles";

import { dec_to_dms, ra_to_hours } from "../../units";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  SurveyLinkList: {
    display: "inline-block",
  },
  SurveyLink: {
    backgroundColor: theme.palette.primary.main,
    padding: "2px 15px",
    margin: "3px",
    display: "inline-block",
    color: theme.palette.secondary.main,
    borderRadius: "5px",
  },
  submitButton: {
    border: "none",
    backgroundColor: theme.palette.primary.main,
    cursor: "pointer",
    padding: 0,
    margin: 0,
    fontWeight: "bold",
    color: theme.palette.secondary.main,
    textDecoration: "none",
    borderRadius: "5px",
  },
}));

const SurveyLink = ({ name, url }) => {
  const styles = useStyles();
  return (
    <a href={url} target="_blank" rel="noreferrer">
      <div className={styles.SurveyLink}>{name}</div>
    </a>
  );
};

const SurveyLinkForm = ({ name, url, formData, urlEncoded = false }) => {
  const styles = useStyles();
  return (
    <div className={styles.SurveyLink}>
      <form
        method="post"
        target="_blank"
        rel="noreferrer"
        action={url}
        encType={
          urlEncoded
            ? "application/x-www-form-urlencoded"
            : "multipart/form-data"
        }
      >
        {Object.entries(formData).map(([key, value]) => (
          <input type="hidden" key={key} name={key} value={value} />
        ))}
        <button type="submit" className={styles.submitButton}>
          {name}
        </button>
      </form>
    </div>
  );
};

SurveyLink.propTypes = {
  name: PropTypes.string.isRequired,
  url: PropTypes.string,
};

SurveyLink.defaultProps = {
  url: null,
};

SurveyLinkForm.propTypes = {
  name: PropTypes.string.isRequired,
  url: PropTypes.string.isRequired,
  formData: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types
  urlEncoded: PropTypes.bool,
};

SurveyLinkForm.defaultProps = {
  urlEncoded: false,
};

const SurveyLinkList = ({ ra, dec, id }) => {
  const styles = useStyles();
  const ra_hrs = ra_to_hours(ra, ":");
  const dec_hrs = dec_to_dms(dec, ":");
  // TODO: const thumbnail_timestamp = "TODO";
  const photometry = useSelector((state) => state.photometry);
  const objPhotometry = photometry?.[id];

  let isDetected = false;
  let magErr = Infinity;
  let timeStamp = null;

  if (objPhotometry) {
    objPhotometry.forEach((phot) => {
      if (phot.mag) {
        isDetected = true;
        if (phot.magerr < magErr) {
          magErr = phot.magerr;

          // convert MJD to unix timestamp in ms
          timeStamp = dayjs.unix((phot.mjd - 40587) * 86400.0).utc();
        }
      }
    });
  }

  return (
    <div className={styles.SurveyLinkList}>
      <SurveyLink
        name="ADS"
        url={`https://ui.adsabs.harvard.edu/search/q=object%22${ra}%20${
          dec > 0 ? "%2B" : ""
        }${dec}%3A0%201%22&sort=date%20desc%2C%20bibcode%20desc&p_=0`}
      />
      <SurveyLink
        name="Aladin"
        url={`http://aladin.unistra.fr/AladinLite/?target=${ra_to_hours(
          ra,
          "%20",
        )}${dec > 0 ? "%2B" : ""}${dec_to_dms(
          dec,
          "%20",
          false,
        )}&fov=0.08&survey=P%2FPanSTARRS%2FDR1%2Fcolor-z-zg-g`}
      />
      <SurveyLink
        name="CFHT"
        url={`http://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/cadcbin/megapipe/imc.pl?lang=en&object=&size=256&ra=${ra}&dec=${dec}`}
      />
      <SurveyLinkForm
        name="CRTS"
        url="http://nunuku.caltech.edu/cgi-bin/getcssconedb_release_img.cgi"
        formData={{
          RA: `${ra}`,
          Dec: `${dec}`,
          Rad: "0.5",
          IMG: "nun",
          DB: "photcat",
          OUT: "csv",
          SHORT: "short",
          PLOT: "plot",
        }}
      />
      <SurveyLink
        name="DECam"
        url={`http://legacysurvey.org/viewer?ra=${ra}&dec=${dec}&zoom=14`}
      />
      <SurveyLink
        name="DSS2"
        url={`https://archive.stsci.edu/cgi-bin/dss_search?v=poss2ukstu_red&r=${ra}&d=${dec}&e=J2000&h=15.0&w=15.0&f=gif&c=none&fov=NONE&v3=`}
      />
      <SurveyLink
        name="Extinction"
        url={`https://ned.ipac.caltech.edu/extinction_calculator?in_csys=Equatorial&in_equinox=J2000.0&obs_epoch=2000.0&ra=${ra_to_hours(
          ra,
          null,
        )}&dec=${dec_to_dms(dec, null)}`}
      />
      <SurveyLinkForm
        name="FIRST"
        url="https://third.ucllnl.org/cgi-bin/firstcutout"
        formData={{
          RA: `${ra_to_hours(ra, " ")} ${dec_to_dms(dec, " ")}`,
          Equinox: "J2000",
          Text: "0",
        }}
      />
      <SurveyLink
        name="Gaia DR2"
        url={`http://vizier.u-strasbg.fr/viz-bin/VizieR?-source=I/345/gaia2&-out.add=_r&-out.add=2C_DEJ&-sort=_r&-to=&-out.max=20&-meta.ucd=2&-meta.foot=1&-c=${ra_hrs}+${dec_hrs}&-c.rs=10`}
      />
      <SurveyLink
        name="Galex"
        url={`http://galex.stsci.edu/GR6/?page=searchresults&type=mastform&ra=${ra}&dec=${dec}&radius=1.0&outputformat=HTML_Table&max_records=20&action=Search`}
      />
      <SurveyLink
        name="HEASARC"
        url={`https://heasarc.gsfc.nasa.gov/cgi-bin/vo/datascope/jds.pl?position=${encodeURIComponent(
          ra_to_hours(ra, " "),
        )}%2C${encodeURIComponent(dec_to_dms(dec, " "))}&size=0.25`}
      />
      {isDetected && (
        <SurveyLinkForm
          name="MPChecker"
          url="https://minorplanetcenter.net/cgi-bin/mpcheck.cgi"
          formData={{
            year: timeStamp.format("YYYY"),
            month: timeStamp.format("MM"),
            day: `${timeStamp.format("DD")}.${Math.floor(
              (parseInt(timeStamp.format("H"), 10) / 24) * 10,
            )}`,
            which: "pos",
            ra: ra_to_hours(ra, " "),
            decl: dec_to_dms(dec, " "),
            TextArea: undefined,
            radius: "5",
            limit: "24.0",
            oc: "500",
            sort: "d",
            mot: "h",
            tmot: "s",
            pdes: "u",
            needed: "f",
            ps: "n",
            type: "p",
          }}
          urlEncoded
        />
      )}
      <SurveyLink
        name="NED"
        url={`http://nedwww.ipac.caltech.edu/cgi-bin/nph-objsearch?lon=${ra}d&lat=${dec}d&radius=1.0&search_type=Near+Position+Search`}
      />
      <SurveyLink
        name="PTF"
        url={`https://irsa.ipac.caltech.edu/applications/ptf/#id=Hydra_ptf_ptf_image_pos&RequestClass=ServerRequest&DoSearch=true&intersect=CENTER&size=0.0083333334&subsize=0.13888889000000001&mcenter=all&dpLevel=l1&UserTargetWorldPt=${ra};${dec};EQ_J2000&SimpleTargetPanel.field.resolvedBy=nedthensimbad&ptfField=&ccdId=&projectId=ptf&searchName=ptf_image_pos&shortDesc=Search%20by%20Position&isBookmarkAble=true&isDrillDownRoot=true&isSearchResult=true`}
      />
      <SurveyLink
        name="SDSS"
        url={`http://skyserver.sdss.org/dr16/en/tools/chart/navi.aspx?opt=G&ra=${ra}&dec=${dec}&scale=0.25`}
      />
      <SurveyLink
        name="SIMBAD"
        url={`http://simbad.u-strasbg.fr/simbad/sim-coo?protocol=html&NbIdent=us=30&Radius.unit=arcsec&CooFrame=FK5&CooEpoch=2000&CooEqui=2000&Coord=${ra}d+${dec}d`}
      />
      <SurveyLink
        name="Subaru"
        url={`http://smoka.nao.ac.jp/search?RadorRec=radius&longitudeC=${ra}&latitudeC=${dec}&instruments=SUP&instruments=FCS&instruments=HDS&instruments=OHS&instruments=IRC&instruments=CIA&instruments=COM&instruments=CAC&instruments=MIR&instruments=MCS&instruments=K3D&instruments=HIC&instruments=FMS&obs_mod=IMAG&obs_mod=SPEC&data_typ=OBJECT&dispcol=FRAMEID&dispcol=DATE_OBS&dispcol=&dispcol=FILTER&dispcol=WVLEN&dispcol=UT_START&dispcol=EXPTIME&radius=10&action=Search`}
      />
      <SurveyLink
        name="TNS"
        url={`https://wis-tns.org/search?&ra=${ra}&decl=${dec}&radius=10&coords_unit=arcsec`}
      />
      <SurveyLink
        name="VizieR"
        url={`http://vizier.u-strasbg.fr/viz-bin/VizieR?-source=&-out.add=_r&-out.add=2C_DEJ&-sort=_r&-to=&-out.max=20&-meta.ucd=2&-meta.foot=1&-c=${ra_hrs}+${dec_hrs}&-c.rs=10`}
      />
      <SurveyLink
        name="VLT"
        url={`http://archive.eso.org/wdb/wdb/eso/eso_archive_main/query?ra=${ra_hrs}&dec=${dec_hrs}&amp;deg_or_hour=hours&box=00+10+00&max_rows_returned=500`}
      />
      <SurveyLink
        name="WISE"
        url={`http://irsa.ipac.caltech.edu/applications/wise/#id=Hydra_wise_wise_1&RequestClass=ServerRequest&DoSearch=true&intersect=CENTER&subsize=0.16666666800000002&mcenter=all&schema=allsky-4band&dpLevel=3a&band=1,2,3,4&UserTargetWorldPt=${ra};${dec};EQ_J2000&SimpleTargetPanel.field.resolvedBy=nedthensimbad&preliminary_data=no&coaddId=&projectId=wise&searchName=wise_1&shortDesc=Position&isBookmarkAble=true&isDrillDownRoot=true&isSearchResult=true`}
      />
      <SurveyLink
        name="ZTF"
        url={`https://irsa.ipac.caltech.edu/applications/ztf/#id=Hydra_ztf_ztf_image_pos&RequestClass=ServerRequest&DoSearch=true&intersect=CENTER&subsize=0.13888889000000001&mcenter=all&dpLevel=sci,ref,diff&UserTargetWorldPt=${ra};${dec};EQ_J2000&SimpleTargetPanel.field.resolvedBy=nedthensimbad&ztfField=&ccdId=&projectId=ztf&searchName=ztf_image_pos&shortDesc=Search%20by%20Position&isBookmarkAble=true&isDrillDownRoot=true&isSearchResult=true`}
      />
    </div>
  );
};

SurveyLinkList.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  id: PropTypes.string.isRequired,
};

export default SurveyLinkList;
