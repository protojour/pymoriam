import{s as M,p as c,q as p,r as m,b as v,f as h,u as A,v as u,i as f,h as w,n as g,w as x,x as b,t as B,d as C,j as E}from"./scheduler.DY_PyhZ8.js";import{g as R}from"./Label.Dg7id-lx.js";import{S as $,i as q}from"./index.BEGIuHZD.js";function z(l){let t,s;return{c(){t=p("title"),s=B(l[1])},l(e){t=m(e,"title",{});var a=v(t);s=C(a,l[1]),a.forEach(h)},m(e,a){f(e,t,a),w(t,s)},p(e,a){a&2&&E(s,e[1])},d(e){e&&h(t)}}}function L(l){let t,s,e=l[1]&&z(l),a=[{xmlns:"http://www.w3.org/2000/svg"},{viewBox:"0 0 32 32"},{fill:"currentColor"},{preserveAspectRatio:"xMidYMid meet"},{width:l[0]},{height:l[0]},l[2],l[3]],o={};for(let i=0;i<a.length;i+=1)o=c(o,a[i]);return{c(){t=p("svg"),e&&e.c(),s=p("path"),this.h()},l(i){t=m(i,"svg",{xmlns:!0,viewBox:!0,fill:!0,preserveAspectRatio:!0,width:!0,height:!0});var r=v(t);e&&e.l(r),s=m(r,"path",{d:!0}),v(s).forEach(h),r.forEach(h),this.h()},h(){A(s,"d","M16 28L9 21 10.4 19.6 16 25.2 21.6 19.6 23 21z"),u(t,o)},m(i,r){f(i,t,r),e&&e.m(t,null),w(t,s)},p(i,[r]){i[1]?e?e.p(i,r):(e=z(i),e.c(),e.m(t,s)):e&&(e.d(1),e=null),u(t,o=R(a,[{xmlns:"http://www.w3.org/2000/svg"},{viewBox:"0 0 32 32"},{fill:"currentColor"},{preserveAspectRatio:"xMidYMid meet"},r&1&&{width:i[0]},r&1&&{height:i[0]},r&4&&i[2],r&8&&i[3]]))},i:g,o:g,d(i){i&&h(t),e&&e.d()}}}function S(l,t,s){let e,a;const o=["size","title"];let i=x(t,o),{size:r=16}=t,{title:d=void 0}=t;return l.$$set=n=>{s(5,t=c(c({},t),b(n))),s(3,i=x(t,o)),"size"in n&&s(0,r=n.size),"title"in n&&s(1,d=n.title)},l.$$.update=()=>{s(4,e=t["aria-label"]||t["aria-labelledby"]||d),s(2,a={"aria-hidden":e?void 0:!0,role:e?"img":void 0,focusable:Number(t.tabindex)===0?!0:void 0})},t=b(t),[r,d,a,i,e]}class Y extends ${constructor(t){super(),q(this,t,S,L,M,{size:0,title:1})}}export{Y as C};