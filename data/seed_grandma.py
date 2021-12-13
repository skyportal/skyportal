# -*- coding: utf-8 -*-
"""

"""
import os
import csv
import glob
import requests
import pandas as pd
from astropy.time import Time
from astropy.table import Table
import matplotlib.pyplot as plt
import numpy as np
from math import isnan
import urllib3
from astropy.io import fits
import owncloud
import yaml
import sys

urllib3.disable_warnings()

datapath = 'KN-Catcher-ReadyforO4/'

user=sys.argv[1]
mdp=sys.argv[2]
ext_to_keep = ['.vot','.vots','.fit','.fts','fits']
oc = owncloud.Client('https://grandma-owncloud.lal.in2p3.fr/', verify_certs=False)
oc.login(user, mdp)

ztf_list = ['ZTF21abbzjeq','ZTF21abdwdwo','ZTF21abfaohe','ZTF21abfmbix','ZTF21ablssud','ZTF21abotose','ZTF21absvlrr','ZTF21abultbr','ZTF21abxkven','ZTF21abxlpdl','ZTF21abyplur','ZTF21acceboj']

def file_exists(path):
	if os.path.isfile(os.getcwd()+ path):
		return True
	else:
		return False

def fix_telescope_name(name):
    if '/' in name:
        name = name.replace('/',' ')
    return name

def fix_phonenumber(phonenumber):
    if phonenumber[:2] == '00':
        phonenumber = '+' + phonenumber[2:]
    return phonenumber

def login_to_owncloud():
	ztf_files = {}
	for ztf_id in ztf_list:
		files = [x.path for x in oc.list('/KN-Catcher-ReadyforO4/'+ztf_id, depth=1)]
		files_cleaned = []
		for file in files:

			if any(ext in file for ext in ext_to_keep) and file[-1]!='/':
				files_cleaned.append(file)
		ztf_files[ztf_id] = files_cleaned
	for ztf_id in ztf_files.keys():
		for file in ztf_files[ztf_id]:
			print(file)
			if not os.path.isdir(os.getcwd()+'/KN-Catcher-ReadyforO4'): os.makedirs(os.getcwd()+'/KN-Catcher-ReadyforO4')
			if not os.path.isdir(os.getcwd()+'/KN-Catcher-ReadyforO4/'+ztf_id): os.makedirs(os.getcwd()+'/KN-Catcher-ReadyforO4/'+ztf_id)
			if file_exists(file.replace('stack-target','stack.target')):
				print(file.replace('stack-target','stack.target').split('/')[3] + " has already been downloaded")
			else:
				oc.get_file(file, file[1:].replace('stack-target','stack.target'))
				print("downloaded : "+file.replace('stack-target','stack.target').split('/')[3]+" successfully")
	return ztf_files

def telescope_name(username, filefits):
	if username=='AbastumaniTeam':
		username='Abastumani-T70'
	if username=='Baransky':
		username='Lisnyky-AZT-8'
	if (username=='Boust' or username=='boust' or username=='dominique' or username=='kugel' or username=='Kugel'):
		username='T40-A77DAU'
	if username=='Boutigny':
		username='Vallieres'
	if username=='Broens':
		username='T-BRO'
	if username=='Burkhonov':
		username='UBAI/NT-60'
	if username=='Cailleau':
		username='Teams'
	if username=='Cejudo':
		username='Gallinero'
	if (username=='Eggenstein' or username=='eggenstein'):
		hdu = fits.open(filefits)
		hdr=hdu[0].header
		if "OBSERVAT" in hdr:
			username=hdr["OBSERVAT"]
			if "T24" in username:
				username="iTel-24"
			if "T17" in username:
				username="iTel-17"
			if "SRO" in username:
				username="SRO"
		else:
			username="Omegon203"
		print("le tel d'eggenstein s'appelle"+str(username))
	if username=='Freeberg':
		username='C11FREE'
	if username=='Galdies':
		username='T-GAL'
	if username=='Gokuldass':
		username='VIRT'
	if username=='Granier':
		username='T-GRA'
	if username=='Galdies':
		username='T-GAL'
	if (username=='Jaquiery' or username=='jaquiery') :
		username='Beverly-Begg'
	if (username=='Leonini'or username=='MontarrentiObs'):
		username='Montarrenti'
	if username=='Leroy':
		username='Uranoscope'
	if username=='Marchais':
		username='T-CAT'
	if username=='Masek':
		username='FRAM-Auger'
	if username=='Leroy':
		username='Uranoscope'
	if username=='Noysena':
		username='TRT'
	if username=='Popowicz':
		username='SUTO2'
	if username=='Rousselot':
		username='N250-ROU'
	if (username=='SERRAU' or username=='Serrau'):
		username='MSXD-A77'
	if username=='Song':
		username='Tibet-50'
	if username=='Taylor':
		username='T-PDA'
	if username=='bayard':
		username='C11-BATY'
	if username=='kneip':
		username='K26'
	if username=='richmond':
		username='RIT'
	return username

def filter_name_grandma(filename):
	try:
			filt_int=filename.split('_')[4].split('.')[0]
			if filt_int in ["001B","002B","003B","004B","005B","006B","007B","008B","009B","010B","TB","B","T400A"]:
				filt_int="grandma::b"
			if filt_int in ["001R","002R","003R","004R","005R","006R","007R","008R","009R","010R","TR","R","Rc"]:
				filt_int="grandma::r"
			if filt_int in ["I","Ic"]:
				filt_int="grandma::i"
			if filt_int in ["C","Clear","clear"]:
				filt_int="grandma::c"
			if filt_int in ["L","lumen"]:
				filt_int="grandma::l"
			if filt_int in ["G","TG"]:
				filt_int="grandma::g"
			if filt_int in ["g","sG","sloanG"]:
				filt_int="grandma::g"
			if filt_int in ["r","sR","sloanR","SR"]:
				filt_int="grandma::g"
			if filt_int in ["g","sG","sloanR"]:
				filt_int="grandma::g"
			if filt_int in ["i","sloanI"]:
				filt_int="grandma::i"
			if filt_int in ["v","V"]:
				filt_int="grandma::v"
			if filt_int in ["w"]:
				filt_int="grandma::w"
	except:
			filt_int=filename.split('_')[4]
			if filt_int in ["001B","002B","003B","004B","005B","006B","007B","008B","009B","010B","TB","B","T400A"]:
				filt_int="grandma::b"
			if filt_int in ["001R","002R","003R","004R","005R","006R","007R","008R","009R","010R","TR","R","Rc"]:
				filt_int="grandma::r"
			if filt_int in ["I","Ic"]:
				filt_int="grandma::i"
			if filt_int in ["C","Clear","clear"]:
				filt_int="grandma::c"
			if filt_int in ["L","lumen"]:
				filt_int="grandma::l"
			if filt_int in ["G","TG"]:
				filt_int="grandma::g"
			if filt_int in ["g","sG","sloanG"]:
				filt_int="grandma::g"
			if filt_int in ["r","sR","sloanR","SR"]:
				filt_int="grandma::g"
			if filt_int in ["g","sG","sloanR"]:
				filt_int="grandma::g"
			if filt_int in ["i","sloanI"]:
				filt_int="grandma::i"
			if filt_int in ["v","V"]:
				filt_int="grandma::v"
			if filt_int in ["w"]:
				filt_int="grandma::w"
	return filt_int

def ztf_filters(filter):
	return 'ztf'+filter

def treat_alert(ztf_list):
	ztf_dict = {}
	for ztf_id in ztf_list:
		dict_temp = {}
		dict_temp['ztf'] = {
			'mjd' : [],
			'filter' : [],
			'mag' : [],
			'magerr' : [],
			'limiting_mag' : [],
			'magsys' : [],
			'ra' : [],
			'dec' : []
			}
		ztf_dict[ztf_id] = dict_temp
		print("***************************************")

		print(ztf_id)


		# =============================================================================
		# Retrieve Fink data about the alert
		# =============================================================================
		# get data for the alert
		r = requests.post(
		  'http://134.158.75.151:24000/api/v1/objects',
		  json={
		    'objectId': ztf_id,
		    'output-format': 'json'
		  }
		)

		# Format output in a DataFrame
		pdf = pd.read_json(r.content)
		firstdate_ztf = Time(pdf['i:jd'].values[-1],format='jd').mjd
		delay_ztf = Time(pdf['i:jd'],format='jd').mjd - firstdate_ztf
		timemjd_ztf=Time(pdf['i:jd'],format='jd').mjd
		timeutc_ztf=Time(pdf['i:jd'],format='jd').iso
		mags_ztf = pdf['i:magpsf']
		magerrs_ztf = pdf['i:sigmapsf']
		# Labels of ZTF filters
		filtdic = {1: 'g', 2: 'r'}
		magsupp_ztf = pdf['i:diffmaglim']
		#print(len(mags_ztf))
		rasztf=np.zeros(len(mags_ztf))
		decsztf=np.zeros(len(mags_ztf))
		ztf_filts = []
		for filt in pdf['i:fid']:
			ztf_filts.append('ztf'+filtdic[filt])

		ztf_dict[ztf_id]['ztf']['mjd'].extend(timemjd_ztf)
		ztf_dict[ztf_id]['ztf']['filter'].extend(ztf_filts)
		ztf_dict[ztf_id]['ztf']['mag'].extend(mags_ztf)
		ztf_dict[ztf_id]['ztf']['magerr'].extend(magerrs_ztf)
		ztf_dict[ztf_id]['ztf']['limiting_mag'].extend(magsupp_ztf)
		ztf_dict[ztf_id]['ztf']['magsys'].extend(np.full(len(mags_ztf),'ab'))
		ztf_dict[ztf_id]['ztf']['ra'].extend(np.zeros(len(mags_ztf)))
		ztf_dict[ztf_id]['ztf']['dec'].extend(np.zeros(len(mags_ztf)))

		data_files = glob.glob(datapath+ztf_id+'/*.target.vot',recursive = True)
		data_fits = glob.glob(datapath+ztf_id+'/*.f*t*',recursive = True)


		print("NB target.vot: " +str(len(np.array(data_files)))+" NB fits: "+str(np.array(len(data_fits))))

		mags_ul = []
		filters = []
		delays_ztf = []
		delays_ztf_ul = []
		filters_ul = []
		username_ul = []
		real_filters = []
		timemjd = []
		timeutc = []
		detect = []
		flags = []
		filename_vec=[]
		for filefits in data_fits:
		#filename = data_files[1]
			#print(filefits)
			name_fits=filefits.split(".f")[0]
			#print(name_fits)
			try:
				filename=glob.glob(name_fits+'*.target.vot',recursive = True)[0]
				#print(filefits,filename)
				try:
					data = Table.read(filename)
					username = filename.split('_')[2]
					date  = filename.split('_')[3]
					date_obs = Time(date.split('T')[0]+' '+date.split('T')[1].replace('-',':'))
					date_obs=Time(str(data['time'][0]))
					if "2021" not in str(date_obs):
						date_obs = Time(date.split('T')[0]+' '+date.split('T')[1].replace('-',':'))
					if (isnan(float(data['mag_calib'])) or (data['magerr'] > 0.2)):
						print("erreur in mag value: "+ data['mag_calib'])
					else:
							telescope = telescope_name(username, filefits)
							if ztf_id in ztf_dict:
								if telescope in ztf_dict[ztf_id]:
									ztf_dict[ztf_id][telescope]['mjd'].append(date_obs.mjd)
									ztf_dict[ztf_id][telescope]['filter'].append(filter_name_grandma(filename))
									ztf_dict[ztf_id][telescope]['mag'].append(float(data['mag_calib']))
									ztf_dict[ztf_id][telescope]['magerr'].append(float(data['magerr']))
									ztf_dict[ztf_id][telescope]['limiting_mag'].append(float(data['mag_limit']))
									ztf_dict[ztf_id][telescope]['magsys'].append('ab')
									ztf_dict[ztf_id][telescope]['ra'].append(float(data['ra']))
									ztf_dict[ztf_id][telescope]['dec'].append(float(data['dec']))
								else:
									ztf_dict[ztf_id][telescope] = {
		                            'mjd' : [date_obs.mjd],
		                            'filter' : [filter_name_grandma(filename)],
		                            'mag' : [float(data['mag_calib'])],
		                            'magerr' : [float(data['magerr'])],
		                            'limiting_mag' : [float(data['mag_limit'])],
		                            'magsys' : ["ab"],
		                            'ra' : [float(data['ra'])],
		                            'dec' : [float(data['dec'])]
									}
							else:
								dict_temp = {}
								dict_temp[telescope] = {
		                            'mjd' : [date_obs.mjd],
		                            'filter' : [filter_name_grandma(filename)],
		                            'mag' : [float(data['mag_calib'])],
		                            'magerr' : [float(data['magerr'])],
		                            'limiting_mag' : [float(data['mag_limit'])],
		                            'magsys' : ["ab"],
		                            'ra' : [float(data['ra'])],
		                            'dec' : [float(data['dec'])]
									}
								ztf_dict[ztf_id] = dict_temp

				except:
					print("Erreur in "+filename)
			except:

				print("No results from "+filefits)

	return ztf_dict

def to_yaml(str_name, name):
    filepath = str_name + '.yaml'
    with open(filepath, 'w') as outfile:
        yaml.dump(name, outfile, default_flow_style=False, sort_keys=False)

def create_dir(directory):
    if not os.path.isdir(directory):
       os.makedirs(directory)

def ztf_to_csv(telescopes, telescope, ztfDir, ztf_id, telescope_name):
    df = pd.DataFrame(data=telescopes[telescope])
    df.sort_values("mjd", ascending=False)
    final_path = ztfDir +"/"+ ztf_id +"_"+ telescope_name + ".csv"
    df.to_csv(final_path, index=False)

def to_sources(sources, ztf_dict, ztf_id,collaborations):
    sources.append({
        'id' : ztf_id,
        'ra' : float(ztf_dict[ztf_id]['ztf']['ra'][0]),
        'dec' : float(ztf_dict[ztf_id]['ztf']['dec'][0]),
        'group_ids' : collaborations
    })

    return sources

def to_candidates(candidates, values, telescope, ztf_id):
    passed_at = Time(values['mjd'][0], format='mjd').isot
    if telescope !="ztf":
        candidates.append({
            'id' : ztf_id,
            'filter_ids' : ["=ztfr"],
            'ra' : float(values['ra'][0]),
            'dec' : float(values['dec'][0]),
            'varstar' : True,
            'altdata' : {
                'simbad' : {
                    'class' : "default class"
                }
            },
            'passed_at' : passed_at,
            'alias' : ["default alias"]
        })
    else:
        candidates.append({
            'id' : ztf_id,
            'filter_ids' : ["=ztfr"],
            'varstar' : True,
            'altdata' : {
                'simbad' : {
                    'class' : "default class"
                }
            },
            'passed_at' : passed_at,
            'alias' : ["default alias"]
        })

    return candidates

def to_photometry(photometry, ztf_id, telescope, telescope_name, values, collaborations):
    if telescope !="ztf":
        photometry.append({
            'obj_id' : ztf_id,
            'instrument_id' : '=' + telescope + "_instrument",
            'assignment_id' : 1,
            'file' : 'csv'+"/" + ztf_id + "/"+ ztf_id + "_" + telescope_name + ".csv",
            'group_ids' : collaborations,
            'stream_ids' : ['=ztf_public','=ztf_partnership'],
            'ra' : float(values['ra'][0]),
            'dec' : float(values['dec'][0])
        })
    else:
        photometry.append({
            'obj_id' : ztf_id,
            'instrument_id' : '=' + telescope + "_instrument",
            'assignment_id' : 1,
            'file' : 'csv'+"/" + ztf_id + "/"+ ztf_id + "_" + telescope_name + ".csv",
            'group_ids' : collaborations,
            'stream_ids' : ['=ztf_public','=ztf_partnership'],
        })

    return photometry
def to_instruments(instruments, telescope, telescopes_list):

    instruments.append({
    '=id': telescope+"_instrument",
    'band': 'optical',
    'name': telescope+"_instrument",
    'telescope_id': '=' + telescope,
    'filters': telescopes_list[telescope],
    'type': 'imager'
    })

    return instruments

def to_telescopes(telescopes, telescope):
    tel_data = pd.read_csv(os.getcwd()+"/csv/telescopes_info.csv", keep_default_na=True)
    data = tel_data.loc[tel_data['name'] == telescope]
    
    tel_temp = {
    'diameter': 0,
    'name': telescope,
    'nickname': telescope,
    'skycam_link': None,
    '=id': telescope
    }
    if len(data) !=1 and data[2]!='' and data[2]!=null:
        tel_temp['lat'] = data[2]
    else:
        tel_temp['lat'] = 0
    if len(data) !=1 and data[3]!='' and data[3]!=null:
        tel_temp['lon'] = data[3]
    else:
        tel_temp['lon'] = 0
    if len(data) !=1 and data[4]!='' and data[4]!=null:
        tel_temp['elevation'] = data[4]
    else:
        tel_temp['elevation'] = 0
        
    
    telescopes.append(tel_temp)

    return telescopes

def to_groups():
	filename = os.getcwd()+"/csv/grandma_collaborations.csv"
	groups = []
	with open(filename) as f:
		lines = f.read().splitlines()[1:]

		for l in lines:
			groups.append({
			'name': l.split(',')[1],
			'=id' : l.split(',')[1]
			})

	groups.append({
	'name': 'Program A',
	'=id' : 'program_A'
	})
	groups.append({
	'name': 'Program B',
	'=id' : 'program_B'
	})

	return groups

def to_users():
    users = []
    with open(os.getcwd()+'/csv/grandma_users.csv') as f:
        lines = f.read().splitlines()[1:]
        
        for l in lines:
            if l.split(',')[5] == '':
                users.append({
                'username': l.split(',')[1],
                'first_name': l.split(',')[2],
                'last_name': l.split(',')[3],
                'contact_email': l.split(',')[4],
                'contact_phone': fix_phonenumber(l.split(',')[6]),
                'collaboration': l.split(',')[7],
                'admin': l.split(',')[8]
                })
            else:
                users.append({
                'username': l.split(',')[1],
                'first_name': l.split(',')[2],
                'last_name': l.split(',')[3],
                'contact_email': l.split(',')[4],
                'oauth_uid': l.split(',')[5],
                'contact_phone': fix_phonenumber(l.split(',')[6]),
                'collaboration': l.split(',')[7],
                'admin': l.split(',')[8]
                })


    users.append({
	'username' : 'testadmin',
	'roles' : ['Super admin'],
	'=id' : 'testadmin'
	})

    users.append({
	'username' : 'groupadmin',
	'roles' : ['Group admin'],
	'=id' : 'groupadmin'
	})

    users.append({
	'username' : 'fulluser',
	'roles' : ['Full user'],
	'=id' : 'fulluser'
	})

    users.append({
	'username' : 'viewonlyuser',
	'roles' : ['View only'],
	'=id' : 'viewonlyuser'
	})

    return users

def to_streams():
	streams = []
	streams.append({'name': 'ZTF Public','altdata':{'collection':'ZTF_alerts', 'selector': [1]},'=id':'ztf_public'})
	streams.append({'name': 'ZTF Public+Partnership','altdata':{'collection':'ZTF_alerts', 'selector': [1, 2]},'=id':'ztf_partnership'})
	streams.append({'name': 'ZTF Public+Partnership+Caltech','altdata':{'collection':'ZTF_alerts', 'selector': [1, 2, 3]},'=id':'ztf_caltech'})

	return streams

def to_filters():
	filters = []
	filters.append({'name': 'ZTF R','group_id':'=program_B','stream_id':'=ztf_public','=id':'ztfr'})

	return filters

def to_db_seed():
	db_seed = {}
	db_seed['user'] = {'file' : 'users.yaml'}
	db_seed['streams'] = {'file' : 'streams.yaml'}
	db_seed['groups'] = {'file' : 'groups.yaml'}
	db_seed['filters'] = {'file' : 'filters.yaml'}
	db_seed['telescope'] = {'file' : 'telescopes.yaml'}
	db_seed['instrument'] = {'file' : 'instruments.yaml'}
	#db_seed['taxonomy'] = {'file' : 'taxonomy_sitewide.yaml'}
	db_seed['sources'] = {'file' : 'sources.yaml'}
	db_seed['candidates'] = {'file' : 'candidates.yaml'}
	db_seed['photometry'] = {'file' : 'photometry.yaml'}

	return db_seed

def get_collaborations_list():
	filename = os.getcwd()+"/csv/grandma_collaborations.csv"
	groups = []
	with open(filename) as f:
		lines = f.read().splitlines()[1:]

		for l in lines:
			groups.append('='+l.split(',')[1])
	return groups


def create_csv_and_yaml(ztf_dict):
	telescopes_list = {}
	instruments = []
	telescopes = []
	sources = []
	candidates = []
	photometry = []
	collaborations = get_collaborations_list()

	for ztf_id in ztf_dict:

		sources = to_sources(sources, ztf_dict, ztf_id,collaborations)

		for telescope, values in ztf_dict[ztf_id].items():
			for filter in ztf_dict[ztf_id][telescope]['filter']:

				if telescope not in telescopes_list:
					telescopes_list[telescope] = [filter]

				elif filter not in telescopes_list[telescope]:
					telescopes_list[telescope].append(filter)

			candidates = to_candidates(candidates, values, telescope, ztf_id)

			csvDir =  os.getcwd()+"/csv"
			create_dir(csvDir)

			ztfDir =  csvDir + "/" + ztf_id
			create_dir(ztfDir)

			telescope_name = fix_telescope_name(telescope)
			ztf_to_csv(ztf_dict[ztf_id], telescope, ztfDir, ztf_id, telescope_name)

			photometry = to_photometry(photometry, ztf_id, telescope, telescope_name, values, collaborations)

	for telescope in telescopes_list:
		instruments = to_instruments(instruments, telescope, telescopes_list)
		telescopes = to_telescopes(telescopes, telescope)


	to_yaml('instruments', instruments)
	to_yaml('telescopes', telescopes)
	to_yaml('sources', sources)
	to_yaml('candidates', candidates)
	to_yaml('photometry', photometry)

	groups = to_groups()
	to_yaml('groups', groups)

	users = to_users()
	to_yaml('users', users)

	streams = to_streams()
	to_yaml('streams', streams)

	filters = to_filters()
	to_yaml('filters', filters)

	db_seed = to_db_seed()
	to_yaml('db_seed', db_seed)

files = login_to_owncloud()
print("successfully retrieved all KN_catcher data")

ztf_dict = treat_alert(ztf_list)
print("successfully read data from properly working files")

create_csv_and_yaml(ztf_dict)
print("successfully created all yaml and photometry files as csv for skyportal")
