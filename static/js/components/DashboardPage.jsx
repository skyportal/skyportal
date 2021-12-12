import React from 'react';
import { useState, useEffect }from "react";
import { POST } from "../API";


//import LoadingSpinner from '../../components/LoadingSpinner';
//import { useGlobalReducer } from '../../contexts/GlobalContext';
import Select from 'react-select';

import ListAlerts from './ListAlerts'

import Axios from 'axios';


const AppButton = ({ onPress, title }) => {
  return (
    <button onClick={onPress} style={styles.appButtonContainer}>
      <p style={styles.appButtonText}>{title}</p>
    </button>
  );
};

/*function DashboardPage({navigation}) {
  //const db
  const [relatedSources, setRelateSources] = useState([]);
  const [telescopeName, setTelescopeName] = useState([]);
  const [eventId, setEventId] = useState([]);
  const [navigationID,setNavigationId]=useState(0)

  const [relatedTransients, setRelatedTransients] = useState([])

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/id').then((response)=>{
      setEventId(response.data)
    })
  },[]);

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/sources').then((response)=>{
      setRelateSources(response.data)
    })
  },[]);

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/telescopes').then((response)=>{
      setTelescopeName(response.data)
    })
  },[]);

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/transients_related').then((response)=>{
      setRelatedTransients(response.data)

      console.log('setRelatedTransients=>',response.data)
    })

  },[]);

  // const SubmitReview = () =>{
  //   Axios.post('http://localhost:19007/api/insert', {
  //     totoId: totoId,
  //     totoName: totoName,
  //   }).then(() => {
  //     alert("Succesful insert");
  //   })
  // }

  //revision slider
  const [value, setValue] = React.useState(30);
  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  //choice box telescope
  const telescopesOptions = telescopeName.map(telescope => ({
    value: telescope.name,
    label: telescope.name
  }));

  //choice box sources
  const sourcesOptions = relatedSources.map(source => ({
    value: source.name,
    label: source.name
  }));

  console.log('relatedTransients =',relatedTransients)
  if(navigationID==1){
    return(
        <div>
          <AppButton
            title="Retour"
            onPress={() => {
              setNavigationId(0)
            }
          }/>
          <ListAlerts />
        </div>
    )
  }
  return (
    <div>
      {eventId.map((val)=> {
          return (<p style={styles.paragraph}>S190814bv - Campaign on going {"\n"}
          ID: {val.id}</p>)
        })}
      <p>Telescope Obs</p>
      <Select
            isMulti
            name="telescopes"
            options={telescopesOptions}
            className="basic-multi-select"
            classNamePrefix="select"
            menuPortalTarget={document.body}
          />
      <p>          Related Sources (eg. OTs) </p>
      <Select
            isMulti
            name="sources"
            options={sourcesOptions}
            className="basic-multi-select"
            classNamePrefix="select"
            menuPortalTarget={document.body}
          />
      {relatedTransients.map((val)=> {
          return (<p style={styles.text}>Transients: {val.alias}</p>)
        })}
      <AppButton
          title="List of alerts"
          onPress={() => {
            setNavigationId(1)
          }
        }/>
    </div>
  );
  
};*/

const DashboardPage = () => {
  const [relatedSources, setRelateSources] = useState([]);
  const [telescopeName, setTelescopeName] = useState([]);
  const [eventId, setEventId] = useState([]);
  const [navigationID,setNavigationId]=useState(0)

  const [relatedTransients, setRelatedTransients] = useState([])

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/id').then((response)=>{
      setEventId(response.data)
    })
  },[]);

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/sources').then((response)=>{
      setRelateSources(response.data)
    })
  },[]);

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/telescopes').then((response)=>{
      setTelescopeName(response.data)
    })
  },[]);

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/transients_related').then((response)=>{
      setRelatedTransients(response.data)

      console.log('setRelatedTransients=>',response.data)
    })

  },[]);

  // const SubmitReview = () =>{
  //   Axios.post('http://localhost:19007/api/insert', {
  //     totoId: totoId,
  //     totoName: totoName,
  //   }).then(() => {
  //     alert("Succesful insert");
  //   })
  // }

  //revision slider
  const [value, setValue] = React.useState(30);
  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  //choice box telescope
  const telescopesOptions = telescopeName.map(telescope => ({
    value: telescope.name,
    label: telescope.name
  }));

  //choice box sources
  const sourcesOptions = relatedSources.map(source => ({
    value: source.name,
    label: source.name
  }));

  const LOG_ERROR = `relatedTransients = ${relatedTransients}`;
  const logError = (errorInfo) => POST(`/api/internal/log`, LOG_ERROR, errorInfo);

  console.log('relatedTransients =', relatedTransients)
  if(navigationID==1){
    return(
        <div>
          <AppButton
            title="Retour"
            onPress={() => {
              setNavigationId(0)
            }
          }/>
          <ListAlerts />
        </div>
    )
  }
  return (
    <div>
      <h1>Dashboard Grandma</h1>
      {eventId.map((val)=> {
          return (<p style={styles.paragraph}>S190814bv - Campaign on going {"\n"}
          ID: {val.id}</p>)
        })}
      <p>Telescope Obs</p>
      <Select
            isMulti
            name="telescopes"
            options={telescopesOptions}
            className="basic-multi-select"
            classNamePrefix="select"
            menuPortalTarget={document.body}
          />
      <p>          Related Sources (eg. OTs) </p>
      <Select
            isMulti
            name="sources"
            options={sourcesOptions}
            className="basic-multi-select"
            classNamePrefix="select"
            menuPortalTarget={document.body}
          />
      {relatedTransients.map((val)=> {
          return (<p style={styles.text}>Transients: {val.alias}</p>)
        })}
      <AppButton
          title="List of alerts"
          onPress={() => {
            setNavigationId(1)
          }
        }/>
    </div>
  );
};


export default DashboardPage;

const styles = {
  container: {
    padding: 8,
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#cfe2f3ff',
  },
  paragraph: {
    margin: 18,
    marginTop: 30,
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  text: {
    fontSize: 16,
    textAlign: 'center',
    margin: 20,
  },
  multiselect: {
    marginLeft: 30,
    marginRight: 30,
    marginBottom: 0,
    marginTop: 0,
    padding: 20
  },
  item: {
    flex: 0.5,
    backgroundColor: 'white',
    borderWidth: 2,
    margin: 5,
  },
  card_skymap:{
    marginLeft: 30,
    marginRight: 30,
    marginBottom: 30,
    borderWidth: 2,
  },
  card:{
    marginLeft: 30,
    marginRight: 30,
    border: "none",
    boxShadow: "none"
  },
  card_info:{
    marginLeft: 30,
    marginRight: 30,
    marginTop: 90,
    borderWidth: 2,
  },
  appButtonContainer: {
    backgroundColor: '#ceccccff',
    borderRadius: 18,
    paddingVertical: 10,
    marginLeft: 90,
    marginRight: 90,
    marginBottom: 15,
  },
  appButtonText: {
    fontSize: 18,
    color: 'black',
    alignSelf: 'center',
  }
};
