import{s as C,C as v,e as K,a as S,c as L,b as Q,g as q,f as w,u as b,B as k,D as p,i as z,h as R,E as D,F as T,G as B,H as A,A as V,k as W,I as X,J as G}from"./scheduler.DY_PyhZ8.js";import{S as Y,i as Z,b as H,d as I,m as J,a as g,t as f,e as M}from"./index.BEGIuHZD.js";import{a as _,b as l,t as tt,e as et,P as at}from"./Label.Dg7id-lx.js";import{d as ot}from"./strataStore.lIzWCy2V.js";const st=e=>({}),N=e=>({}),rt=e=>({}),O=e=>({});function it(e){let t;const o=e[13].default,c=v(o,e,e[16],null);return{c(){c&&c.c()},l(d){c&&c.l(d)},m(d,s){c&&c.m(d,s),t=!0},p(d,s){c&&c.p&&(!t||s&65536)&&T(c,o,d,d[16],t?A(o,d[16],s,null):B(d[16]),null)},i(d){t||(g(c,d),t=!0)},o(d){f(c,d),t=!1},d(d){c&&c.d(d)}}}function nt(e){let t,o,c;const d=e[13].icon,s=v(d,e,e[16],O);return o=new at({props:{type:"short",capitalizeFirst:!0,$$slots:{default:[it]},$$scope:{ctx:e}}}),{c(){s&&s.c(),t=S(),H(o.$$.fragment)},l(r){s&&s.l(r),t=q(r),I(o.$$.fragment,r)},m(r,$){s&&s.m(r,$),z(r,t,$),J(o,r,$),c=!0},p(r,$){s&&s.p&&(!c||$&65536)&&T(s,d,r,r[16],c?A(d,r[16],$,rt):B(r[16]),O);const h={};$&65536&&(h.$$scope={dirty:$,ctx:r}),o.$set(h)},i(r){c||(g(s,r),g(o.$$.fragment,r),c=!0)},o(r){f(s,r),f(o.$$.fragment,r),c=!1},d(r){r&&w(t),s&&s.d(r),M(o,r)}}}function ct(e){let t,o,c,d,s,r,$;o=new _({props:{gap:8,itemAlign:"center",$$slots:{default:[nt]},$$scope:{ctx:e}}});const h=e[13].dropdown,u=v(h,e,e[16],N);return{c(){t=K("button"),H(o.$$.fragment),c=S(),u&&u.c(),this.h()},l(a){t=L(a,"BUTTON",{id:!0,class:!0,type:!0,title:!0,tabindex:!0});var i=Q(t);I(o.$$.fragment,i),c=q(i),u&&u.l(i),i.forEach(w),this.h()},h(){b(t,"id",e[1]),b(t,"class","strata--button svelte-1xlq0cm"),t.disabled=e[3],b(t,"type",e[6]),b(t,"title",e[2]),b(t,"tabindex",d=e[9]?-1:0),k(t,"round",e[4]),k(t,"setButton",e[5]),p(t,"width",e[0]),p(t,"height",e[7]),p(t,"--accent-color",e[10]?"var(--ui-colors-x-light-1)":l(e[11],4)),p(t,"--border-color",e[8]==="secondary"?l(e[11],4):"transparent"),p(t,"--background-base",l(e[11],e[10]?4:1)),p(t,"--background-hover",e[10]?`var(--ix-${e[11]}-main-dark)`:l(e[11],2)),p(t,"--background-active",l(e[11],(e[10],3)))},m(a,i){z(a,t,i),J(o,t,null),R(t,c),u&&u.m(t,null),s=!0,r||($=[D(t,"click",e[14]),D(t,"focus",e[15])],r=!0)},p(a,[i]){const m={};i&65536&&(m.$$scope={dirty:i,ctx:a}),o.$set(m),u&&u.p&&(!s||i&65536)&&T(u,h,a,a[16],s?A(h,a[16],i,st):B(a[16]),N),(!s||i&2)&&b(t,"id",a[1]),(!s||i&8)&&(t.disabled=a[3]),(!s||i&64)&&b(t,"type",a[6]),(!s||i&4)&&b(t,"title",a[2]),(!s||i&512&&d!==(d=a[9]?-1:0))&&b(t,"tabindex",d),(!s||i&16)&&k(t,"round",a[4]),(!s||i&32)&&k(t,"setButton",a[5]),i&1&&p(t,"width",a[0]),i&128&&p(t,"height",a[7]),i&1024&&p(t,"--accent-color",a[10]?"var(--ui-colors-x-light-1)":l(a[11],4)),i&256&&p(t,"--border-color",a[8]==="secondary"?l(a[11],4):"transparent"),i&1024&&p(t,"--background-base",l(a[11],a[10]?4:1)),i&1024&&p(t,"--background-hover",a[10]?`var(--ix-${a[11]}-main-dark)`:l(a[11],2)),i&1024&&p(t,"--background-active",l(a[11],(a[10],3)))},i(a){s||(g(o.$$.fragment,a),g(u,a),s=!0)},o(a){f(o.$$.fragment,a),f(u,a),s=!1},d(a){a&&w(t),M(o),u&&u.d(a),r=!1,V($)}}}function dt(e,t,o){let c,d;W(e,ot,n=>o(12,d=n));let{$$slots:s={},$$scope:r}=t,{id:$="strata-"+Math.random().toString(36)}=t,{title:h=""}=t,{disabled:u=!1}=t,{round:a=!1}=t,{setButton:i=!1}=t,{type:m="button"}=t,{width:y="fit-content"}=t,{height:E="32px"}=t,{btnType:x="primary"}=t,{noTab:F=!1}=t,P=tt[x];y=i?"unset":y,X(()=>et($));function U(n){G.call(this,e,n)}function j(n){G.call(this,e,n)}return e.$$set=n=>{"id"in n&&o(1,$=n.id),"title"in n&&o(2,h=n.title),"disabled"in n&&o(3,u=n.disabled),"round"in n&&o(4,a=n.round),"setButton"in n&&o(5,i=n.setButton),"type"in n&&o(6,m=n.type),"width"in n&&o(0,y=n.width),"height"in n&&o(7,E=n.height),"btnType"in n&&o(8,x=n.btnType),"noTab"in n&&o(9,F=n.noTab),"$$scope"in n&&o(16,r=n.$$scope)},e.$$.update=()=>{e.$$.dirty&4352&&o(10,c=!d&&["success","warning","danger","info"].includes(x))},[y,$,h,u,a,i,m,E,x,F,c,P,d,s,U,j,r]}class ut extends Y{constructor(t){super(),Z(this,t,dt,ct,C,{id:1,title:2,disabled:3,round:4,setButton:5,type:6,width:0,height:7,btnType:8,noTab:9})}}export{ut as B};
