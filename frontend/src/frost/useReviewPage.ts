import {useCallback,useEffect,useRef,useState} from 'react';
import {useLive} from '../data/live';
import {errorMessage} from './data';

interface ReviewPage<T> {items:T[];total:number;limit:number;offset:number}

/** Shared bounded review transport; responses belong to the current API/path only. */
export function useReviewPage<T extends {assignment_id:string}>(path:string){
  const {api}=useLive();
  const [response,setResponse]=useState<{client:typeof api;path:string;page:ReviewPage<T>}|null>(null);
  const [error,setError]=useState(''),[loading,setLoading]=useState(true),[more,setMore]=useState(false),[revision,setRevision]=useState(0);
  const nextRequest=useRef<AbortController|null>(null);
  const reload=useCallback(()=>setRevision(value=>value+1),[]);
  const value=response?.client===api&&response.path===path?response.page:null;
  useEffect(()=>{
    const controller=new AbortController();nextRequest.current?.abort();setResponse(null);setMore(false);setError('');setLoading(true);
    void api.json<ReviewPage<T>>(path,{signal:controller.signal},{limit:3}).then(page=>{
      if(!controller.signal.aborted)setResponse({client:api,path,page});
    }).catch(failure=>{if(!controller.signal.aborted)setError(errorMessage(failure));}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    const refresh=()=>{if(!document.hidden)reload();};
    window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);window.addEventListener('sf-review-updated',refresh);
    return()=>{controller.abort();nextRequest.current?.abort();window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh);window.removeEventListener('sf-review-updated',refresh);};
  },[api,path,revision,reload]);
  async function loadMore(){
    if(!value||loading||more)return;
    const controller=new AbortController();nextRequest.current=controller;setMore(true);setError('');
    try{
      const page=await api.json<ReviewPage<T>>(path,{signal:controller.signal},{limit:3,offset:value.items.length});
      if(!controller.signal.aborted)setResponse({client:api,path,page:{...page,items:[...value.items,...page.items].filter((item,index,items)=>items.findIndex(other=>other.assignment_id===item.assignment_id)===index)}});
    }catch(failure){if(!controller.signal.aborted){setResponse(null);setError(errorMessage(failure));}}
    finally{if(!controller.signal.aborted)setMore(false);}
  }
  function collapse(){nextRequest.current?.abort();setMore(false);if(value)setResponse({client:api,path,page:{...value,items:value.items.slice(0,3)}});}
  return {value,error,loading,more,reload,loadMore,collapse};
}
