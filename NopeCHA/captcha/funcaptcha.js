(()=>{function D(){if("ancestorOrigins"in location){let t=location.ancestorOrigins,n=t[1]??t[0];if(n)return n.split("/")[2]}let e=document.referrer;return e?e.split("/")[2]:location.origin}var h=chrome;var x="https://api.nopecha.com",i="https://www.nopecha.com",L="https://developers.nopecha.com",_e={doc:{url:L,automation:{url:`${L}/guides/extension_advanced/#automation-build`}},api:{url:x,recognition:{url:`${x}/recognition`},status:{url:`${x}/status`}},www:{url:i,annoucement:{url:`${i}/json/announcement.json`},demo:{url:`${i}/demo`,hcaptcha:{url:`${i}/demo/hcaptcha`},recaptcha:{url:`${i}/demo/recaptcha`},funcaptcha:{url:`${i}/demo/funcaptcha`},awscaptcha:{url:`${i}/demo/awscaptcha`},turnstile:{url:`${i}/demo/turnstile`},textcaptcha:{url:`${i}/demo/textcaptcha`},perimeterx:{url:`${i}/demo/perimeterx`}},manage:{url:`${i}/manage`},pricing:{url:`${i}/pricing`},setup:{url:`${i}/setup`}},discord:{url:`${i}/discord`},github:{url:`${i}/github`,release:{url:`${i}/github/release`}}};function E(e){let t=("68deee3b46050627b187a31ec5204173fb5d74e2bb6e5ffeab6b7595130fab39"+e).split("").map(n=>n.charCodeAt(0));return q(t)}var P=new Uint32Array(256);for(let e=256;e--;){let t=e;for(let n=8;n--;)t=t&1?3988292384^t>>>1:t>>>1;P[e]=t}function q(e){let t=-1;for(let n of e)t=t>>>8^P[t&255^n];return(t^-1)>>>0}async function u(e,t){let n=""+[+new Date,performance.now(),Math.random()],[a,o]=await new Promise(r=>{h.runtime.sendMessage([n,e,...t],r)});if(a===E(n))return o}function b(){let e;return t=>e||(e=t().finally(()=>e=void 0),e)}var oe=b(),m;function O(){return oe(async()=>(m||(m=await u("settings::get",[])),m))}function F(e){m&&(m={...m,...e},N(m))}function _(){return m}function l(e){return new Promise(t=>setTimeout(t,e))}var z=[];function T(e,t){e.timedout=!1,z.push(e);let n,a=setInterval(async()=>{await U(e,_())||(clearTimeout(n),clearInterval(a))},400);t&&(n=setTimeout(()=>clearInterval(a),t),e.timedout=!0)}async function U(e,t){if(e.timedout)return!1;let n=e.condition(t);if(n===e.running())return!1;if(!n&&e.running())return e.quit(),!1;if(n&&!e.running()){for(;!e.ready();)await l(200);return e.start(),!1}}function N(e){z.forEach(t=>U(t,e))}function W(){h.runtime.connect({name:"stream"}).onMessage.addListener(t=>{t.event==="settingsUpdate"&&F(t.settings)})}function S(e){if(document.readyState!=="loading")setTimeout(e,0);else{let t;t=()=>{removeEventListener("DOMContentLoaded",t),e()},addEventListener("DOMContentLoaded",t)}}var Oe=b();var re=["#home_children_button","#wrong_children_button","#wrongTimeout_children_button","button[data-theme*=verifyButton]","[class*=game-fail] .button",".error .button"],G=["#root","#app","#home","#wrong","#wrongTimeout",".container[dir]"].join(", "),k,C=!1;function V(){return!!document.querySelector(G)}function j(){C=!0;let e=()=>{ie(),document.querySelectorAll(G).forEach(t=>{k.observe(t,{childList:!0})})};k=new MutationObserver(e),e()}function Q(){k.disconnect(),C=!1}function K(){return C}async function ie(){await l(400),re.map(e=>document.querySelector(e)).filter(e=>e).map(e=>e.click())}function ce(e,t){let n=document.createElement("canvas");return n.width=e,n.height=t,n}function M(e){return e.toDataURL("image/jpeg").replace(/data:image\/[a-z]+;base64,/g,"")}function se(e){try{e.getContext("2d").getImageData(0,0,1,1)}catch{return!0}return!1}async function I(e,t,n=1e4){if(!t&&!e.complete&&!await new Promise(c=>{let d=setTimeout(()=>{c(!1)},n);e.addEventListener("load",()=>{clearTimeout(d),c(!0)})}))return;let a=ce(e.naturalWidth||t?.clientWidth,e.naturalHeight||t?.clientHeight);return a.getContext("2d").drawImage(e,0,0),!se(a)&&a}async function B(e){let n=getComputedStyle(e).backgroundImage;if(!n||n==="none")if("src"in e&&e.src)n=`url("${e.src}")`;else return;if("computedStyleMap"in e){let s=e.computedStyleMap().get("background-image");if(s instanceof CSSImageValue){let f=await I(s,e);if(f)return f}}let a=/"(.+)"/.exec(n);if(!a)return;n=a[1];let o=document.createElement("a");if(o.href=n,new URL(o.href).origin===document.location.origin){let s=new Image;s.crossOrigin="anonymous",s.src=n;let f=await I(s);if(f)return f}let r=await u("fetch::asData",[n,{}]),c=new Image;c.crossOrigin="anonymous",c.src=r.data;let d=await I(c);if(d)return d}function ue(e,t,n,a){let o=(a*t+n)*4;return[e[o],e[o+1],e[o+2]]}function le(e,t){return e.every(n=>n<=t)}function de(e,t){return e.every(n=>n>=t)}function $(e,t=0,n=230,a=.99){let o=e.getContext("2d"),r=o.canvas.width,c=o.canvas.height;if(r===0||c===0)return!0;let d=o.getImageData(0,0,r,c).data,s=0;for(let w=0;w<c;w++)for(let v=0;v<r;v++){let A=ue(d,r,v,w);(le(A,t)||de(A,n))&&s++}return s/(r*c)>a}function J(){return[]}function X(e){return new Promise(t=>{e.push(t)})}function g(e){e.forEach(t=>t()),e.splice(0)}async function Y(e,t){let n={v:h.runtime.getManifest().version,key:me(e)};return n.url=await u("tab::getURL",[]),n}function me(e){return!e.keys||!e.keys.length?e.key:e.keys[Math.floor(Math.random()*e.keys.length)]}var p=J(),H,y=!1;function ee(){return R()!==void 0}function te(){y=!0,g(p),H=new MutationObserver(e=>{let t=R();for(let n of e)if(n.type==="childList"&&n.removedNodes.length&&["app","game"].includes(n.target.id)){setTimeout(()=>g(p),200);return}t===1&&e.length===24&&!document.querySelector(".loading-spinner")&&setTimeout(()=>g(p),200),t===2&&[8,13].includes(e.length)&&!document.querySelector(".loading-spinner")&&setTimeout(()=>g(p),200)}),H.observe(document,{childList:!0,subtree:!0,attributes:!0}),fe()}function ne(){H.disconnect(),y=!1,g(p)}function ae(){return y}var ge={[0]:{async getTask(){let e=document.querySelector("#game_children_text h2"),t=document.querySelector("#game_challengeItem_image"),n=[...document.querySelectorAll("#game_children_challenge a")];if(!(!e||!t||n.length!==6))return{payload:{type:"funcaptcha",task:e.textContent,image_data:[t.src.replace(/data:image\/[a-z]+;base64,/g,"")]},cells:n}},async solution(e,t){e.cells.forEach((n,a)=>{t.data[a]&&n.click()})}},[1]:{async getTask(){let e=document.querySelector(".tile-game h2"),t=[...document.querySelectorAll(".challenge-container button")];if(!e||t.length!==6)return;let n=await B(t[0]);if(n&&!$(n))return{payload:{type:"funcaptcha",task:e.textContent,image_data:[M(n)]},cells:t}},async solution(e,t){e.cells.forEach((n,a)=>{t.data[a]&&n.click()})}},[2]:{async getTask(){let e=document.querySelector(".match-game h2"),t=document.querySelector(".key-frame-image");if(!e||!t)return;let n=await B(t);if(n&&!$(n))return{payload:{type:"funcaptcha_match",task:e.textContent,image_data:[M(n)]}}},async solution(e,t){let n=document.querySelector(".right-arrow"),a=t.data.indexOf(!0);for(let r=0;r<a;r++)n.click(),await l(100);await l(500),document.querySelector(".button").click()}}},pe=[["script[src*=tile-game-ui]",0],[".tile-game",1],[".match-game",2]];function R(){return pe.filter(([e])=>document.querySelector(e)).map(([e,t])=>t)[0]}var Z=!1;async function fe(){if(!Z)for(Z=!0;y;){let e=R();if(e===void 0){await l(500);continue}let t=ge[e],n=await t.getTask();if(!n){await l(500);continue}let a=_(),o=new Date().valueOf(),r=await u("api::recognition",[{...n.payload,...await Y(a,!0)}]);if(!r||"error"in r){await l(2e3);continue}let c=new Date().valueOf();if(a.funcaptcha_solve_delay){let s=a.funcaptcha_solve_delay_time-c+o;s>0&&await l(s)}await t.solution(n,r);let d=setTimeout(()=>{g(p)},1e3*5);await X(p),clearTimeout(d)}}async function he(){W(),await O(),await u("tab::registerDetectedCaptcha",["funcaptcha"]);let e=D();T({name:"funcaptcha/auto-open",condition:t=>t.enabled&&t.funcaptcha_auto_open&&!t.disabled_hosts.includes(e),ready:V,start:j,quit:Q,running:K}),T({name:"funcaptcha/auto-solve",condition:t=>t.enabled&&t.funcaptcha_auto_solve&&!t.disabled_hosts.includes(e),ready:ee,start:te,quit:ne,running:ae})}S(he);})();
