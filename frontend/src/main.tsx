import {Component,Suspense,lazy,type ReactNode} from 'react';
import {createRoot} from 'react-dom/client';
import {createBrowserRouter,RouterProvider,Navigate,useLocation} from 'react-router-dom';
import {AppProvider,useApp} from './data/store';
import {DEMO_ENABLED} from './brand';
import Shell from './components/Shell';
import {Skeleton,Button} from './components/ui';
import './styles.css';
import './winter-glass.css';
import './reference-match.css';
const PublicPages=lazy(()=>import('./pages/PublicPages'));
const WorkspacePages=lazy(()=>import('./pages/WorkspacePages'));
const AccountPages=lazy(()=>import('./pages/AccountPages'));
function Workspace(){const {user}=useApp();const location=useLocation();if(!DEMO_ENABLED||!user)return <Navigate replace to={`/login?returnTo=${encodeURIComponent(location.pathname+location.search)}`}/>;if(user.status==='disabled')return <Navigate replace to="/account-disabled"/>;if(!user.verified||user.status==='pending')return <Navigate replace to="/verify-email"/>;const path=location.pathname;if((path.startsWith('/app/admin')&&user.role!=='admin')||(/^\/app\/(review-queue|assigned|reviews|review-history)(\/|$)/.test(path)&&user.role!=='analyst'))return <Navigate replace to="/403"/>;const account=/^\/app\/(admin|profile|settings|notifications|help)(\/|$)/.test(path);return <Shell><Suspense fallback={<Skeleton/>}>{account?<AccountPages/>:<WorkspacePages/>}</Suspense></Shell>;}
class ErrorBoundary extends Component<{children:ReactNode},{failed:boolean}>{state={failed:false};static getDerivedStateFromError(){return {failed:true};}render(){return this.state.failed?<div className="utility-screen"><div className="utility-inner"><p className="utility-code">500</p><h1>A quiet interruption.</h1><p>The interface could not finish loading. Your saved demo metadata is still in this browser.</p><Button onClick={()=>location.reload()}>Reload the page</Button></div></div>:this.props.children;}}
const router=createBrowserRouter([{path:'/app/*',element:<Workspace/>},{path:'*',element:<PublicPages/>}]);
createRoot(document.getElementById('root')!).render(<ErrorBoundary><AppProvider><Suspense fallback={<div className="workspace"><Skeleton/></div>}><RouterProvider router={router}/></Suspense></AppProvider></ErrorBoundary>);
