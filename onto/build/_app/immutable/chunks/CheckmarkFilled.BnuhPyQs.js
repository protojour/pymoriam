import{s as A,p as v,q as p,r as c,b as f,f as h,u as m,v as g,i as x,h as w,n as u,w as b,x as M,t as E,d as B,j as C}from"./scheduler.DY_PyhZ8.js";import{g as R}from"./Label.Dg7id-lx.js";import{S as $,i as L}from"./index.BEGIuHZD.js";function z(o){let t,s;return{c(){t=p("title"),s=E(o[1])},l(e){t=c(e,"title",{});var i=f(t);s=B(i,o[1]),i.forEach(h)},m(e,i){x(e,t,i),w(t,s)},p(e,i){i&2&&C(s,e[1])},d(e){e&&h(t)}}}function j(o){let t,s,e,i=o[1]&&z(o),n=[{xmlns:"http://www.w3.org/2000/svg"},{viewBox:"0 0 32 32"},{fill:"currentColor"},{preserveAspectRatio:"xMidYMid meet"},{width:o[0]},{height:o[0]},o[2],o[3]],r={};for(let a=0;a<n.length;a+=1)r=v(r,n[a]);return{c(){t=p("svg"),i&&i.c(),s=p("path"),e=p("path"),this.h()},l(a){t=c(a,"svg",{xmlns:!0,viewBox:!0,fill:!0,preserveAspectRatio:!0,width:!0,height:!0});var l=f(t);i&&i.l(l),s=c(l,"path",{d:!0}),f(s).forEach(h),e=c(l,"path",{fill:!0,d:!0,"data-icon-path":!0}),f(e).forEach(h),l.forEach(h),this.h()},h(){m(s,"d","M16,2A14,14,0,1,0,30,16,14,14,0,0,0,16,2ZM14,21.5908l-5-5L10.5906,15,14,18.4092,21.41,11l1.5957,1.5859Z"),m(e,"fill","none"),m(e,"d","M14 21.591L9 16.591 10.591 15 14 18.409 21.41 11 23.005 12.585 14 21.591z"),m(e,"data-icon-path","inner-path"),g(t,r)},m(a,l){x(a,t,l),i&&i.m(t,null),w(t,s),w(t,e)},p(a,[l]){a[1]?i?i.p(a,l):(i=z(a),i.c(),i.m(t,s)):i&&(i.d(1),i=null),g(t,r=R(n,[{xmlns:"http://www.w3.org/2000/svg"},{viewBox:"0 0 32 32"},{fill:"currentColor"},{preserveAspectRatio:"xMidYMid meet"},l&1&&{width:a[0]},l&1&&{height:a[0]},l&4&&a[2],l&8&&a[3]]))},i:u,o:u,d(a){a&&h(t),i&&i.d()}}}function q(o,t,s){let e,i;const n=["size","title"];let r=b(t,n),{size:a=16}=t,{title:l=void 0}=t;return o.$$set=d=>{s(5,t=v(v({},t),M(d))),s(3,r=b(t,n)),"size"in d&&s(0,a=d.size),"title"in d&&s(1,l=d.title)},o.$$.update=()=>{s(4,e=t["aria-label"]||t["aria-labelledby"]||l),s(2,i={"aria-hidden":e?void 0:!0,role:e?"img":void 0,focusable:Number(t.tabindex)===0?!0:void 0})},t=M(t),[a,l,i,r,e]}class Y extends ${constructor(t){super(),L(this,t,q,j,A,{size:0,title:1})}}export{Y as C};