import{w as c}from"./paths.CQM_VkiC.js";import{a as g,S as v}from"./api.B1Xfa_7A.js";import{a as S,e as L,c as N,t as j,i as x,g as O}from"./get.s5tF0M-W.js";import{i as w}from"./isObject.C3e4t58V.js";import{y as U}from"./scheduler.DY_PyhZ8.js";var y=function(){try{var e=S(Object,"defineProperty");return e({},"",{}),e}catch{}}();function P(e,a,o){a=="__proto__"&&y?y(e,a,{configurable:!0,enumerable:!0,value:o,writable:!0}):e[a]=o}var $=Object.prototype,k=$.hasOwnProperty;function z(e,a,o){var s=e[a];(!(k.call(e,a)&&L(s,o))||o===void 0&&!(a in e))&&P(e,a,o)}function A(e,a,o,s){if(!w(e))return e;a=N(a,e);for(var t=-1,d=a.length,n=d-1,i=e;i!=null&&++t<d;){var l=j(a[t]),m=o;if(l==="__proto__"||l==="constructor"||l==="prototype")return e;if(t!=n){var h=i[l];m=void 0,m===void 0&&(m=w(h)?h:x(a[t+1])?[]:{})}z(i,l,m),i=i[l]}return e}function R(e,a,o){return e==null?e:A(e,a,o)}const r={accessPolicies:{},selectedResource:"",resourceList:[],selectedRole:"",roleList:[]},u=c({...r.accessPolicies}),_=c(""+r.selectedResource),p=c([...r.resourceList]),b=c(""+r.selectedRole),f=c([...r.roleList]),E=()=>{u.set({...r.accessPolicies}),_.set(""+r.selectedResource),p.set([...r.resourceList]),b.set(""+r.selectedRole),f.set([...r.roleList])},B=async e=>{if(e&&e.length>0){const a=await g.get(`${v}/acm/domain/${e}/resources`);if(a.ok){const o=await a.json();return p.set(o.map(s=>({id:s.resourceName,header:s.resourceName,label:"Link or description"}))),o}}},D=async()=>{{const e=await g.get(`${v}/acm/roles`);if(e.ok){const a=await e.json();f.set(a.map(o=>({id:o.groupName,header:o.groupName,label:"xx Users"})))}}},I=async(e,a,o)=>{if(!e||!a||!o)return;const s=[{name:"create",allow:!0,rule:'"somethinger" in Profile.ServiceRoles'},{name:"read",allow:!0,rule:'"somethinger" in Profile.ServiceRoles'},{name:"update",allow:!0,rule:'"somethinger" in Profile.ServiceRoles'},{name:"delete",allow:!1,rule:'"somethinger" in Profile.ServiceRoles'}],t=[{name:"foo",allow:!0,rule:'"somethinger" in Profile.ServiceRoles'},{name:"bar",allow:!0,rule:'"somethinger" in Profile.ServiceRoles'},{name:"baz",allow:!0,rule:'"somethinger" in Profile.ServiceRoles'},{name:"bazinga",allow:!1,rule:'"somethinger" in Profile.ServiceRoles'},{name:"spap",allow:!0,rule:'"somethinger" in Profile.ServiceRoles'}],d=[{id:"ap_"+o.id+"_"+a.id,name:o.header+" hotdog policy",updatedAt:new Date,lastUpdatedBy:"mathias",dirty:!1,actions:s},{id:"ap2_"+o.id+"_"+a.id,name:o.header+" custom policy",updatedAt:new Date,lastUpdatedBy:"mathias",dirty:!1,actions:t}],n=U(u);d.forEach(i=>{O(n,[e,a.id,o.id,i.id])||R(n,[e,a.id,o.id,i.id],i)}),u.set(n)},X=async e=>(console.log("FIXME: post this data to api",e),new Promise(a=>a(!0)));export{_ as a,u as b,p as c,E as d,B as e,I as f,D as g,R as h,P as i,X as p,f as r,b as s};