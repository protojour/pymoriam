import{s as h,e as x,a as v,c as w,b as j,f as o,g as k,u as y,D as d,i as $,t as D,d as S,j as z}from"./scheduler.DY_PyhZ8.js";import{S as A,i as E,b as l,d as m,m as u,a as f,t as p,e as g}from"./index.BEGIuHZD.js";import{a as F,P as I,b}from"./Label.Dg7id-lx.js";function P(c){let t;return{c(){t=D(c[0])},l(e){t=S(e,c[0])},m(e,s){$(e,t,s)},p(e,s){s&1&&z(t,e[0])},d(e){e&&o(t)}}}function V(c){let t,e,s,r;return s=new I({props:{type:"short",margin:0,capitalizeFirst:!0,$$slots:{default:[P]},$$scope:{ctx:c}}}),{c(){t=x("div"),e=v(),l(s.$$.fragment),this.h()},l(a){t=w(a,"DIV",{class:!0}),j(t).forEach(o),e=k(a),m(s.$$.fragment,a),this.h()},h(){y(t,"class","running-status svelte-1jomw2"),d(t,"background",c[3]?"var(--ix-disabled-accent)":b(c[1],4))},m(a,n){$(a,t,n),$(a,e,n),u(s,a,n),r=!0},p(a,n){n&10&&d(t,"background",a[3]?"var(--ix-disabled-accent)":b(a[1],4));const i={};n&17&&(i.$$scope={dirty:n,ctx:a}),s.$set(i)},i(a){r||(f(s.$$.fragment,a),r=!0)},o(a){p(s.$$.fragment,a),r=!1},d(a){a&&(o(t),o(e)),g(s,a)}}}function q(c){let t,e;return t=new F({props:{itemAlign:"center",direction:c[2],gap:8,$$slots:{default:[V]},$$scope:{ctx:c}}}),{c(){l(t.$$.fragment)},l(s){m(t.$$.fragment,s)},m(s,r){u(t,s,r),e=!0},p(s,[r]){const a={};r&4&&(a.direction=s[2]),r&27&&(a.$$scope={dirty:r,ctx:s}),t.$set(a)},i(s){e||(f(t.$$.fragment,s),e=!0)},o(s){p(t.$$.fragment,s),e=!1},d(s){g(t,s)}}}function B(c,t,e){let{status:s=""}=t,{color:r="red"}=t,{direction:a="right"}=t,{disabled:n=!1}=t;return c.$$set=i=>{"status"in i&&e(0,s=i.status),"color"in i&&e(1,r=i.color),"direction"in i&&e(2,a=i.direction),"disabled"in i&&e(3,n=i.disabled)},[s,r,a,n]}class C extends A{constructor(t){super(),E(this,t,B,q,h,{status:0,color:1,direction:2,disabled:3})}}export{C as S};
