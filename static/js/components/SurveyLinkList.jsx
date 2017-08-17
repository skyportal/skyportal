import React from 'react'
import { ra_to_hours, dec_to_hours } from '../units';

const SurveyLinkList = ({ ra, dec, id }) => {
  const ra_hrs = ra_to_hours(ra);
  const dec_hrs = dec_to_hours(dec);
  const thumbnail_timestamp = 'TODO';

  return (
    <div>
      <div><a href={`http://nedwww.ipac.caltech.edu/cgi-bin/nph-objsearch?lon=${ra}sd&lat=${dec}sd&radius=1.0&search_type=Near+Position+Search`}>NED</a></div>
      <div><a href={`https://wis-tns.weizmann.ac.il/search?&ra=${ra}s&decl=${dec}s&radius=10&coords_unit=arcsec`}>TNS</a></div>
      <div><a href={`http://secure.lcogt.net/user/supernova/dev/cgi-bin/view_object.cgi?name=iPTF${id}s&ra=${ra}s&dec=${dec}s`}>SNEx</a></div>
      <div><a href={`http://simbad.u-strasbg.fr/simbad/sim-coo?protocol=html&NbIdent=1&Radius=30&Radius.unit=arcsec&CooFrame=FK5&CooEpoch=2000&CooEqui=2000&Coord=${ra}sd+${dec}sd`}>SIMBAD</a></div>
      <div><a href={`http://vizier.u-strasbg.fr/viz-bin/VizieR?-source=&-out.add=_r&-out.add=_RAJ%%2C_DEJ&-sort=_r&-to=&-out.max=20&-meta.ucd=2&-meta.foot=1&-c=${ra_hrs}s+${dec_hrs}s&-c.rs=10`}>VizieR</a></div>
      <div><a href={`javascript:alert('TODO')`}>HEASARC</a></div>
      <div><a href={`http://legacysurvey.org/viewer?ra=${ra}s&dec=${dec}s&zoom=14&layer=decals-dr2`}>DECam</a></div>
      <div><a href={`http://skyview.gsfc.nasa.gov/cgi-bin/runquery.pl?survey=VLA+FIRST+(1.4+Ghz)%%2CNVSS%%2C2MASS-K%%2C2MASS-J%%2CGALEX+NEAR+UV%%2CGALEX+FAR+UV%%2CRASS-CNT+Broad&position=${ra}s%%2C${dec}s`}>SkyView</a></div>
      <div><a href={`http://dotastro.org/PyMPC/PyMPC/?in_1=${ra_hrs}s&in_2=${dec_hrs}s&in_3=${thumbnail_timestamp}s&in_4=50`}>PyMP</a></div>
      <div><a href={`javascript:alert('TODO')`}>MPChecker</a></div>
      <div><a href={`http://nedwww.ipac.caltech.edu/cgi-bin/nph-calc?in_csys=Equatorial&amp;in_equinox=J2000.0&amp;obs_epoch=2000.0&amp;lon=${ra}fd&amp;lat=${dec}fd&amp;pa=0.0&amp;out_csys=Galactic&amp;out_equinox=J2000.0`}>Extinction</a></div>
      <div><a href={`http://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/cadcbin/megapipe/imc.pl?lang=en&object=&size=256&ra=${ra}s&dec=${dec}s`}>CFHT</a></div>
      <div><a href={`http://irsa.ipac.caltech.edu/applications/ptf/#id=Hydra_ptf_ptf_image_pos&RequestClass=ServerRequest&DoSearch=true&intersect=CENTER&subsize=0.13888889000000001&mcenter=all&dpLevel=l1,l2&UserTargetWorldPt=${ra}s;${dec}s;EQ_J2000&SimpleTargetPanel.field.resolvedBy=ned&ptfField=&ccdId=&projectId=ptf&searchName=ptf_image_pos&shortDesc=Search%%20by%%20Position&isBookmarkAble=true&isDrillDownRoot=true&isSearchResult=true`}>IPAC</a></div>
      <div><a href={`http://archive.stsci.edu/cgi-bin/dss_search?h=5.0&w=5.0&f=fits&v=poss2ukstu_red&r=${ra}sd&d=${dec}sd&e=J2000&c=none`}>DSS</a></div>
      <div><a href={`http://irsa.ipac.caltech.edu/applications/wise/#id=Hydra_wise_wise_1&RequestClass=ServerRequest&DoSearch=true&intersect=CENTER&subsize=0.16666666800000002&mcenter=all&schema=allsky-4band&dpLevel=3a&band=1,2,3,4&UserTargetWorldPt=${ra}s;${dec}s;EQ_J2000&SimpleTargetPanel.field.resolvedBy=nedthensimbad&preliminary_data=no&coaddId=&projectId=wise&searchName=wise_1&shortDesc=Position&isBookmarkAble=true&isDrillDownRoot=true&isSearchResult=true`}>WISE</a></div>
      <div><a href={`http://smoka.nao.ac.jp/search?RadorRec=radius&longitudeC=%s&latitudeC=%s&instruments=SUP&instruments=FCS&instruments=HDS&instruments=OHS&instruments=IRC&instruments=CIA&instruments=COM&instruments=CAC&instruments=MIR&instruments=MCS&instruments=K3D&instruments=HIC&instruments=FMS&obs_mod=IMAG&obs_mod=SPEC&data_typ=OBJECT&dispcol=FRAMEID&dispcol=DATE_OBS&dispcol=OBJECT&dispcol=FILTER&dispcol=WVLEN&dispcol=UT_START&dispcol=EXPTIME&radius=10&action=Search`}>Subaru</a></div>
      <div><a href={`http://archive.eso.org/wdb/wdb/eso/eso_archive_main/query?ra=${ra_hrs}s&dec=${dec_hrs}s&amp;deg_or_hour=hours&box=00+10+00&max_rows_returned=500`}>VLT</a></div>
      <div><a href={`javascript:alert('TODO')`}>FIRST</a></div>
      <div><a href={`javascript:alert('TODO')`}>CRTS</a></div>
      <div><a href={`javascript:alert('TODO')`}>Variable Marshal (Search)</a></div>
      <div><a href={`http://adsabs.harvard.edu/cgi-bin/nph-abs_connect?db_key=AST&db_key=PRE&qform=AST&arxiv_sel=astro-ph&arxiv_sel=cond-mat&arxiv_sel=cs&arxiv_sel=gr-qc&arxiv_sel=hep-ex&arxiv_sel=hep-lat&arxiv_sel=hep-ph&arxiv_sel=hep-th&arxiv_sel=math&arxiv_sel=math-ph&arxiv_sel=nlin&arxiv_sel=nucl-ex&arxiv_sel=nucl-th&arxiv_sel=physics&arxiv_sel=quant-ph&arxiv_sel=q-bio&sim_query=YES&ned_query=YES&adsobj_query=YES&aut_logic=OR&obj_logic=OR&author=&object=iptf${id}s%%0D%%0Aptf${id}s%%0D%%0A${ra}s+${dec > 0 ? '%2B' : ''}s${dec}s&start_mon=&start_year=&end_mon=&end_year=&ttl_logic=OR&title=&txt_logic=OR&text=&nr_to_return=200&start_nr=1&jou_pick=ALL&ref_stems=&data_and=ALL&group_and=ALL&start_entry_day=&start_entry_mon=&start_entry_year=&end_entry_day=&end_entry_mon=&end_entry_year=&min_score=&sort=SCORE&data_type=SHORT&aut_syn=YES&ttl_syn=YES&txt_syn=YES&aut_wt=1.0&obj_wt=1.0&ttl_wt=0.3&txt_wt=3.0&aut_wgt=YES&obj_wgt=YES&ttl_wgt=YES&txt_wgt=YES&ttl_sco=YES&txt_sco=YES&version=1`}>ADS</a></div>
    </div>
  )
};


export default SurveyLinkList;
