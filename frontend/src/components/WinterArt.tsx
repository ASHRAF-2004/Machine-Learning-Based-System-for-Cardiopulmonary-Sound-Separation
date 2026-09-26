import type {ReactNode} from 'react';
import {ReferenceArt} from './ReferenceArt';

/** Supporting illustration only. These never represent measured audio or controls. */
export function WinterArt({kind='feather',className=''}:{kind?:'feather'|'collection'|'recordingCollection'|'signal'|'signalFine'|'fusionForest'|'utilitySignal'|'forest'|'dashboardCollection';className?:string}) {
  return <ReferenceArt kind={kind} className={`winter-art winter-${kind} ${className}`}/>;
}

export function WinterNote({children}:{children:ReactNode}) {
  return <aside className="winter-note"><div>{children}</div><WinterArt kind="feather"/></aside>;
}
