import React,{useState} from 'react';
import {ArrowRight,Eye,EyeOff,LockKeyhole,ShieldCheck} from 'lucide-react';
import biaLogo from './assets/bia-logo.png';

export default function LoginPage({setupRequired,onLogin,loading,error,onRetry}){
 const [setup,setSetup]=useState(false),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[showPassword,setShowPassword]=useState(false);
 async function submit(event){
  event.preventDefault();if(busy)return;const form=event.currentTarget;
  setBusy(true);setMessage('');
  try{await onLogin(setup?'setup':'login',Object.fromEntries(new FormData(form)));}
  catch(e){setMessage(e.message);form.elements.password.value='';}
  finally{setBusy(false);}
 }
 return <main className="login-page">
  <section className="login-story" aria-label="BIA project workspace">
   <div className="brand"><img src={biaLogo} alt="BIA Textiles Project Office" className="brand-logo" /></div>
   <div className="login-intro"><span className="eyebrow">ONE WORKSPACE. EVERY PROJECT.</span><h1>From plans{' '}<br/>to progress.</h1><p>A connected view of projects, departments and the people moving them forward.</p></div>
   <div className="login-privacy"><ShieldCheck size={22}/><p>Private team access<span>Your role and department determine the projects and actions available after sign-in.</span></p></div>
  </section>
  <section className="login-panel" aria-labelledby="login-title">
   <div className="login-form-wrap"><span className="login-lock"><LockKeyhole size={24}/></span><h2 id="login-title">{setup?'Set up your workspace':'Sign in to BIA'}</h2><p>{setup?'Create the first administrator account.':'Enter your workspace account to open your dashboard.'}</p>
    {loading?<div className="login-loading" role="status">Checking your session…</div>:<>
     {error&&<div className="error-banner" role="alert">{error}<button type="button" onClick={onRetry}>Try again</button></div>}
     <form onSubmit={submit} aria-label={setup?'Administrator setup':'Sign in'}>
      <fieldset disabled={busy||!!error}>
       {setup&&<label className="field"><span>Your name</span><input name="name" autoComplete="name" required maxLength={80}/></label>}
       <label className="field"><span>Email address</span><input type="email" name="email" autoComplete="username" autoCapitalize="none" spellCheck={false} required maxLength={254}/></label>
       <label className="field"><span>{setup?'Create a password':'Password'}</span><span className="login-password"><input type={showPassword?'text':'password'} name="password" autoComplete={setup?'new-password':'current-password'} minLength={setup?12:1} maxLength={128} required/><button type="button" aria-label={showPassword?'Hide password':'Show password'} aria-pressed={showPassword} onClick={()=>setShowPassword(!showPassword)}>{showPassword?<EyeOff size={19}/>:<Eye size={19}/>}</button></span>{setup&&<small>Use 12–128 characters.</small>}</label>
       {message&&<div className="form-error" role="alert">{message}</div>}
       <button type="submit" className="button primary login-submit">{busy?'Please wait…':setup?'Create administrator':'Sign in'}<ArrowRight size={18}/></button>
      </fieldset>
     </form>
     {setupRequired&&<button className="text-link login-setup" onClick={()=>{setSetup(!setup);setMessage('')}}>{setup?'Back to sign in':'First time? Set up administrator'}</button>}
     {!setupRequired&&<p className="login-help">Need an account or a password reset? Contact your BIA workspace administrator.</p>}
    </>}
   </div><p className="login-footer"><LockKeyhole size={13}/>BIA project portfolio · Private workspace</p>
  </section>
 </main>
}
